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

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.importlib import import_module
from django.utils.translation import ugettext as _

from pootle.core.actions import directory, store
from pootle.core.url_helpers import split_pootle_path
from pootle_app.models.permissions import check_permission
from versioncontrol.utils import hasversioning


@store
def update_from_vcs(request, path_obj, **kwargs):
    if (path_obj.abs_real_path and check_permission('commit', request) and
        hasversioning(path_obj.abs_real_path)):
        link = reverse('pootle-vcs-update',
                       args=split_pootle_path(path_obj.pootle_path))
        text = _('Update from VCS')

        return {
            'icon': 'icon-vcs-update',
            'href': link,
            'text': text,
        }


@store
def commit_to_vcs(request, path_obj, **kwargs):
    if (path_obj.abs_real_path and check_permission('commit', request) and
        hasversioning(path_obj.abs_real_path)):
        link = reverse('pootle-vcs-commit',
                       args=split_pootle_path(path_obj.pootle_path))
        text = _('Commit to VCS')

        return {
            'icon': 'icon-vcs-commit',
            'href': link,
            'text': text,
        }


@directory
def update_dir_from_vcs(request, path_obj, **kwargs):
    if (path_obj.get_real_path() and check_permission('commit', request) and
            hasversioning(path_obj.get_real_path())):
        link = reverse('pootle-vcs-update',
                       args=split_pootle_path(path_obj.pootle_path))
        # Translators: "all" here refers to all files and sub directories in a directory/project.
        text = _('Update all from VCS')

        return {
            'icon': 'icon-vcs-update',
            'href': link,
            'text': text,
        }


@directory
def commit_dir_to_vcs(request, path_obj, **kwargs):
    if (path_obj.get_real_path() and check_permission('commit', request) and
            hasversioning(path_obj.get_real_path())):
        link = reverse('pootle-vcs-commit',
                       args=split_pootle_path(path_obj.pootle_path))
        # Translators: "all" here refers to all files and sub directories in a directory/project.
        text = _('Commit all to VCS')

        return {
            'icon': 'icon-vcs-commit',
            'href': link,
            'text': text,
        }


def rescan_project_files(request, path_obj, **kwargs):
    if check_permission('administrate', request):
        tp = path_obj.translation_project
        link = reverse('pootle-tp-rescan',
                       args=[tp.language.code, tp.project.code])
        text = _("Rescan project files")

        return {
            'icon': 'icon-rescan-files',
            'href': link,
            'text': text,
        }


def update_against_templates(request, path_obj, **kwargs):
    if check_permission('administrate', request):
        tp = path_obj.translation_project
        link = reverse('pootle-tp-update-against-templates',
                       args=[tp.language.code, tp.project.code])
        text = _("Update against templates")

        return {
            'icon': 'icon-update-templates',
            'href': link,
            'text': text,
        }


def delete_path_obj(request, path_obj, **kwargs):
    if check_permission('administrate', request):
        tp = path_obj.translation_project
        link = reverse('pootle-tp-delete-path-obj',
                       args=[tp.language.code, tp.project.code, request.path])

        if path_obj.is_dir:
            text = _("Delete this folder...")
        else:
            text = _("Delete this file...")

        return {
            'icon': 'icon-delete-path',
            'class': 'js-overview-actions-delete-path',
            'href': link,
            'text': text,
        }


def _gen_link_list(request, path_obj, link_funcs, **kwargs):
    """Generates a list of links based on :param:`link_funcs`."""
    links = []

    for link_func in link_funcs:
        link = link_func(request, path_obj, **kwargs)

        if link is not None:
            links.append(link)

    return links


def action_groups(request, path_obj, **kwargs):
    """Returns a list of action links grouped for the overview page.

    :param request: A :class:`~django.http.HttpRequest` object.
    :param path_obj: A :class:`~pootle_app.models.Directory` or
        :class:`~pootle_app.models.Store` object.
    :param kwargs: Extra keyword arguments passed to the underlying functions.
    """
    action_groups = []
    groups = []

    for app in settings.INSTALLED_APPS:
        if app.startswith("django"):
            # XXX ideally, we check for app.startswith("pootle.")
            # but we are not there yet.
            continue

        try:
            module = import_module(app + ".actions")
        except ImportError:
            continue

        groups.extend(module.get_actions())

    groups.append({
        'group': 'manage',
        'group_display': _("Manage"),
        'actions': [
            update_from_vcs,
            commit_to_vcs,
            update_dir_from_vcs,
            commit_dir_to_vcs,
            rescan_project_files,
            update_against_templates,
            delete_path_obj,
        ],
    })

    for group in groups:
        action_links = _gen_link_list(request, path_obj, group['actions'],
                                      **kwargs)

        if action_links:
            group['actions'] = action_links
            action_groups.append(group)

    return action_groups
