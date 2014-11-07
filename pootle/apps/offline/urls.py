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

from django.conf import settings
from django.conf.urls import patterns, url


urlpatterns = patterns('',
    # XXX: Do we really want to let Django serve these files in production?
    # Direct download of translation files.
    #
    # This is also used to provide reverse for the URL.
    url(r'^export/(?P<path>.*)$',
        'django.views.static.serve',
        {'document_root': settings.PODIRECTORY},
        name='pootle-export'),

    # Download and export
    url(r'^download/(?P<pootle_path>.*)/?$',
        'download',
        name='pootle-store-download'),
    url(r'^export-file/xlf/(?P<pootle_path>.*)/?$',
        'export_as_xliff',
        name='pootle-store-export-xliff'),

    # Exporting files
    url(r'^(?P<language_code>[^/]*)/(?P<project_code>[^/]*)/'
        r'(?P<file_path>.*)export/zip/$',
        'export_zip',
        name='pootle-tp-export-zip'),
)
