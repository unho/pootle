#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2014 Zuza Software Foundation
#
# This file is part of Pootle.
#
# Pootle is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# Pootle is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# Pootle; if not, see <http://www.gnu.org/licenses/>.

"""Actions available for the translation project overview page."""

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from pootle.core.actions import directory, store
from pootle_app.models.permissions import check_permission


@store
def download_source(request, path_obj, **kwargs):
    href = None
    if path_obj.name.startswith("pootle-terminology"):
        text = _("Download XLIFF")
        tooltip = _("Download file in XLIFF format")
        href = reverse('pootle-store-export-xliff',
                       args=[path_obj.pootle_path])
    elif path_obj.translation_project.project.is_monolingual:
        text = _('Export')
        tooltip = _('Export translations')
    else:
        text = _('Download')
        tooltip = _('Download file')

    return {
        'icon': 'icon-download',
        'href': href or reverse('pootle-store-download',
                                args=[path_obj.pootle_path]),
        'text': text,
        'tooltip': tooltip,
    }


@store
def download_xliff(request, path_obj):
    if (path_obj.translation_project.project.localfiletype == 'xlf' or
        path_obj.name.startswith("pootle-terminology")):
        return

    return {
        'icon': 'icon-download',
        'href': reverse('pootle-store-export-xliff',
                        args=[path_obj.pootle_path]),
        'text': _("Download XLIFF"),
        'tooltip': _('Download XLIFF file for offline translation'),
    }


@directory
def download_zip(request, path_obj, **kwargs):
    if check_permission('archive', request):
        if not path_obj.is_dir:
            path_obj = path_obj.parent

        language_code = path_obj.translation_project.language.code
        project_code = path_obj.translation_project.project.code

        return {
            'icon': 'icon-download',
            'href': reverse('pootle-tp-export-zip',
                            args=[language_code, project_code, path_obj.path]),
            'text': _('Download (.zip)'),
        }


def upload_zip(request, path_obj, **kwargs):
    if (check_permission('translate', request) or
        check_permission('suggest', request) or
        check_permission('overwrite', request)):
        return {
            'icon': 'icon-upload',
            'class': 'js-popup-inline',
            'href': '#upload',
            'text': _('Upload'),
            'tooltip': _('Upload translation files or archives in .zip '
                         'format'),
        }


def get_actions():
    """Return a list of action groups."""
    return [
        {
            'group': 'translate-offline',
            'group_display': _("Translate offline"),
            'actions': [
                download_source,
                download_xliff,
                download_zip,
                upload_zip,
            ],
        },
    ]
