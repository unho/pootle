# -*- coding: utf-8 -*-
#
# Copyright 2013 Zuza Software Foundation
#
# This file is part of Pootle.
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, see <http://www.gnu.org/licenses/>.

try:
    from django.conf.urls import url
except ImportError: # Django < 1.4
    from django.conf.urls.defaults import url
from django.db.models import Q

from tastypie import fields
from tastypie.authentication import BasicAuthentication
from tastypie.authorization import DjangoAuthorization
from tastypie.utils import trailing_slash

from pootle.core.api import StatisticsModelResource
from pootle_misc.stats import get_raw_stats
from pootle_store.api import StoreResource, UnitResource
from pootle_store.models import Unit
from pootle_store.util import OBSOLETE, UNTRANSLATED, FUZZY
from pootle_translationproject.models import TranslationProject


class TranslationProjectResource(StatisticsModelResource):
    language = fields.ForeignKey('pootle_language.api.LanguageResource',
                                 'language')
    project = fields.ForeignKey('pootle_project.api.ProjectResource', 'project')
    stores = fields.ToManyField(StoreResource, 'stores')

    class Meta:
        queryset = TranslationProject.objects.all()
        resource_name = 'translation-projects'
        fields = [
            'description',
            'language',
            'pootle_path',
            'project',
            'real_path',
            'stores',
        ]
        list_allowed_methods = ['post']
        # HTTP methods allowed for visiting /statistics/ URLs
        statistics_allowed_methods = ['get']
        # List of fields shown when visiting /need-work-units/
        need_work_units_fields = [
            'language',
            'project',
            'units',
        ]
        # HTTP methods allowed for visiting /need-work-units/ URLs
        need_work_units_allowed_methods = ['get']
        authorization = DjangoAuthorization()
        authentication = BasicAuthentication()

    def prepend_urls(self):
        """Returns a list of urlpatterns to be prepend to the default one."""
        urls = super(TranslationProjectResource, self).prepend_urls()
        urls += [
            url(r"^(?P<resource_name>%s)/(?P<%s>\w[\w/-]*)/need-work-units%s$" %
                (self._meta.resource_name, self._meta.detail_uri_name,
                trailing_slash()), self.wrap_view('dispatch_need_work_units'),
                name="api_dispatch_need_work_units"),
        ]
        return urls

    def dispatch_need_work_units(self, request, **kwargs):
        """Handles the HTTP methods on a single TP 'need-work' units list.

        Relies on ``Resource.dispatch`` for the heavy-lifting.
        """
        return self.dispatch('need_work_units', request, **kwargs)

    def get_need_work_units(self, request, **kwargs):
        """Just calls ``Resource.get_detail``

        This gets called in ``Resource.dispatch``
        """
        return self.get_detail(request, **kwargs)

    def retrieve_statistics(self, bundle):
        """Retrieve the statistics for the current resource object."""
        return get_raw_stats(bundle.obj, include_suggestions=True)

    def dehydrate(self, bundle):
        """A hook to allow final manipulation of data.

        It is run after all fields/methods have built out the dehydrated data.

        Useful if you need to access more than one dehydrated field or want to
        annotate on additional data.

        Must return the modified bundle.
        """
        bundle = super(TranslationProjectResource, self).dehydrate(bundle)
        if bundle.request.path.endswith("/need-work-units/"):
            # Remove unnecessary fields for responses to /need_work_units/ URLs
            for field in self._meta.fields:
                if field not in self._meta.need_work_units_fields:
                    bundle.data.pop(field, None)
            criteria = {
                'store__translation_project': bundle.obj,
            }
            unfinished = Unit.objects.filter(**criteria)
            unfinished = unfinished.filter(Q(state=FUZZY) | Q(state=OBSOLETE) |
                                           Q(state=UNTRANSLATED))
            unfinished_list = []
            for unit in unfinished:#TODO look for a way of putting here a list of resource URIs to UnitResources
                unfinished_list.append(UnitResource.get_resource_uri(unit))
                #ModelCResource().get_resource_uri(modelc_object)
            bundle.data['units'] = unfinished_list
        return bundle
