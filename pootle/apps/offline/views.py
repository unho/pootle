#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2014 Zuza Software Foundation
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

import os

from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.encoding import iri_to_uri

from pootle.core.decorators import get_path_obj, permission_required
from pootle_app.project_tree import ensure_target_dir_exists
from pootle_store.decorators import get_store_context
from pootle_store.models import Store
from pootle_store.util import absolute_real_path


@get_store_context('view')
def download(request, store):
    store.sync(update_translation=True)

    return redirect(reverse('pootle-export', args=[store.real_path]))


@get_store_context('view')
def export_as_xliff(request, store):
    """Export given file to xliff for offline translation."""
    path = store.real_path

    if not path:
        # bug 2106
        project = request.translation_project.project

        if project.get_treestyle() == "gnu":
            path = "/".join(store.pootle_path.split(os.path.sep)[2:])
        else:
            parts = store.pootle_path.split(os.path.sep)[1:]
            path = "%s/%s/%s" % (parts[1], parts[0], "/".join(parts[2:]))

    path, ext = os.path.splitext(path)
    export_path = "/".join(['POOTLE_EXPORT', path + os.path.extsep + 'xlf'])
    abs_export_path = absolute_real_path(export_path)

    key = iri_to_uri("%s:export_as_xliff" % store.pootle_path)
    last_export = cache.get(key)

    if (not (last_export and last_export == store.get_mtime() and
        os.path.isfile(abs_export_path))):
        from translate.storage.poxliff import PoXliffFile
        from pootle_misc import ptempfile as tempfile
        import shutil

        ensure_target_dir_exists(abs_export_path)
        outputstore = store.convert(PoXliffFile)
        outputstore.switchfile(store.name, createifmissing=True)
        fd, tempstore = tempfile.mkstemp(prefix=store.name, suffix='.xlf')
        os.close(fd)
        outputstore.savefile(tempstore)
        shutil.move(tempstore, abs_export_path)
        cache.set(key, store.get_mtime(), settings.OBJECT_CACHE_TIMEOUT)

    return redirect(reverse('pootle-export', args=[export_path]))


@get_path_obj
@permission_required('archive')
def export_zip(request, translation_project, file_path):
    from django.utils.timezone import utc

    translation_project.sync()
    pootle_path = translation_project.pootle_path + (file_path or '')

    archivename = '%s-%s' % (translation_project.project.code,
                             translation_project.language.code)

    if file_path.endswith('/'):
        file_path = file_path[:-1]

    if file_path:
        archivename += '-' + file_path.replace('/', '-')

    archivename += '.zip'
    export_path = os.path.join('POOTLE_EXPORT', translation_project.real_path,
                               archivename)
    abs_export_path = absolute_real_path(export_path)

    key = iri_to_uri("%s:export_zip" % pootle_path)
    last_export = cache.get(key)

    tp_time = translation_project.get_mtime().replace(tzinfo=utc)
    up_to_date = False

    if last_export:
        # Make both datetimes tz-aware to avoid a crash here
        last_export = last_export.replace(tzinfo=utc)
        up_to_date = last_export == tp_time

    if not (up_to_date and os.path.isfile(abs_export_path)):
        ensure_target_dir_exists(abs_export_path)
        stores = Store.objects.filter(pootle_path__startswith=pootle_path) \
                              .exclude(file='')
        translation_project.get_archive(stores, abs_export_path)
        cache.set(key, tp_time, settings.OBJECT_CACHE_TIMEOUT)

    return redirect(reverse('pootle-export', args=[export_path]))
