#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2014 Zuza Software Foundation
# Copyright 2013-2014 Evernote Corporation
#
# This file is part of Pootle.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import logging
import os
import json
from urllib import quote, unquote

from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template import loader, RequestContext
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST

from taggit.models import Tag

from pootle.core.browser import (get_children, get_goal_children,
                                 get_goal_parent, get_parent,
                                 get_table_headings)
from pootle.core.decorators import (get_path_obj, get_resource,
                                    permission_required)
from pootle.core.helpers import (get_export_view_context, get_overview_context,
                                 get_translation_context)
from pootle_app.models import Directory
from pootle_app.models.permissions import check_permission
from pootle_app.views.admin.permissions import admin_permissions as admin_perms
from pootle_misc.util import jsonify, ajax_required
from pootle_store.models import Store
from pootle_tagging.decorators import get_goal
from pootle_tagging.forms import GoalForm, TagForm
from pootle_tagging.models import Goal

from .forms import DescriptionForm


ANN_COOKIE_NAME = 'project-announcements'


@get_path_obj
@permission_required('administrate')
def admin_permissions(request, translation_project):
    ctx = {
        'page': 'admin-permissions',

        'translation_project': translation_project,
        'project': translation_project.project,
        'language': translation_project.language,
        'directory': translation_project.directory,
        'feed_path': translation_project.pootle_path[1:],
    }
    return admin_perms(request, translation_project.directory,
                       'translation_projects/admin/permissions.html', ctx)


@get_path_obj
@permission_required('administrate')
def rescan_files(request, translation_project):
    try:
        translation_project.scan_files()

        for store in translation_project.stores.exclude(file='').iterator():
            store.sync(update_translation=True)
            store.update(update_structure=True, update_translation=True)

        messages.success(request, _("Translation project files have been "
                                    "rescanned."))
    except Exception:
        logging.exception(u"Error while rescanning translation project files")
        messages.error(request, _("Error while rescanning translation project "
                                  "files."))

    language = translation_project.language.code
    project = translation_project.project.code
    overview_url = reverse('pootle-tp-overview', args=[language, project, ''])

    return redirect(overview_url)


@get_path_obj
@permission_required('administrate')
def update_against_templates(request, translation_project):
    try:
        translation_project.update_against_templates()
        messages.success(request, _("Translation project has been updated "
                                    "against latest templates."))
    except Exception:
        logging.exception(u"Error while updating translation project against "
                          u"latest templates")
        messages.error(request, _("Error while updating translation project "
                                  "against latest templates."))

    language = translation_project.language.code
    project = translation_project.project.code
    overview_url = reverse('pootle-tp-overview', args=[language, project, ''])

    return redirect(overview_url)


@get_path_obj
@permission_required('administrate')
def delete_path_obj(request, translation_project, dir_path, filename=None):
    """Deletes the path objects under `dir_path` (+ `filename`) from the
    filesystem, including `dir_path` in case it's not a translation project.
    """
    current_path = translation_project.directory.pootle_path
    if current_path != dir_path:
        # HACK see bug 3274
        current_path += dir_path

    try:
        if filename:
            current_path = current_path + filename
            store = get_object_or_404(Store, pootle_path=current_path)
            stores_to_delete = [store]
            directory = None
        else:
            directory = get_object_or_404(Directory, pootle_path=current_path)
            stores_to_delete = directory.stores

        # Delete stores in the current context from the DB and the filesystem.
        for store in stores_to_delete:
            # First from the FS.
            if store.file:
                store.file.storage.delete(store.file.name)

            # From the DB after.
            store.delete()

        if directory:
            directory_is_tp = directory.is_translationproject()

            # First remove children directories from the DB.
            for child_dir in directory.child_dirs.iterator():
                child_dir.delete()

            # Then the current directory (only if we are not in the root of the
            # translation project).
            if not directory_is_tp:
                directory.delete()

            # And finally all the directory tree from the filesystem (excluding
            # the root of the translation project).
            try:
                import shutil
                po_dir = unicode(settings.PODIRECTORY)
                root_dir = os.path.join(po_dir, directory.get_real_path())

                if directory_is_tp:
                    children = [os.path.join(root_dir, child) \
                                for child in os.listdir(root_dir)]
                    child_dirs = filter(os.path.isdir, children)
                    for child_dir in child_dirs:
                        shutil.rmtree(child_dir)
                else:
                    shutil.rmtree(root_dir)
            except OSError:
                messages.warning(request, _("Symbolic link hasn't been "
                                            "removed from the filesystem."))

        if directory:
            messages.success(request, _("Directory and its containing files "
                                        "have been deleted."))
        else:
            messages.success(request, _("File has been deleted."))
    except Exception:
        logging.exception(u"Error while trying to delete %s", current_path)
        messages.error(request, _("Error while trying to delete path."))

    language = translation_project.language.code
    project = translation_project.project.code
    overview_url = reverse('pootle-tp-overview', args=[language, project, ''])

    return redirect(overview_url)


@get_path_obj
@permission_required('commit')
def vcs_commit(request, translation_project, dir_path, filename):
    current_path = translation_project.directory.pootle_path + dir_path

    if filename:
        current_path = current_path + filename
        obj = get_object_or_404(Store, pootle_path=current_path)
        result = translation_project.commit_file(request.user, obj, request)
    else:
        obj = get_object_or_404(Directory, pootle_path=current_path)
        result = translation_project.commit_dir(request.user, obj, request)

    return redirect(obj.get_absolute_url())


@get_path_obj
@permission_required('commit')
def vcs_update(request, translation_project, dir_path, filename):
    current_path = translation_project.directory.pootle_path + dir_path

    if filename:
        current_path = current_path + filename
        obj = get_object_or_404(Store, pootle_path=current_path)
        result = translation_project.update_file(request, obj)
    else:
        obj = get_object_or_404(Directory, pootle_path=current_path)
        result = translation_project.update_dir(request, obj)

    return redirect(obj.get_absolute_url())


@get_path_obj
@permission_required('view')
@get_resource
@get_goal
def overview(request, translation_project, dir_path, filename=None, goal=None):
    from django.utils import dateformat
    from staticpages.models import StaticPage

    if filename:
        ctx = {
            'store_tags': request.store.tag_like_objects,
        }
        template_name = "translation_projects/store_overview.html"
    else:
        ctx = {
            'tp_tags': translation_project.tag_like_objects,
        }
        template_name = "browser/overview.html"

    if (check_permission('translate', request) or
        check_permission('suggest', request) or
        check_permission('overwrite', request)):
        from offline.views import handle_upload_form

        ctx.update({
            'upload_form': handle_upload_form(request, translation_project),
        })

    can_edit = check_permission('administrate', request)

    project = translation_project.project
    language = translation_project.language

    resource_obj = request.store or request.directory

    #TODO enable again some actions when drilling down a goal.
    if goal is None:
        from .action_groups import action_groups
        actions = action_groups(request, resource_obj)
    else:
        actions = []

    action_output = ''

    # TODO: cleanup and refactor, retrieve from cache
    try:
        ann_virtual_path = 'announcements/' + project.code
        announcement = StaticPage.objects.live(request.user).get(
            virtual_path=ann_virtual_path,
        )
    except StaticPage.DoesNotExist:
        announcement = None

    display_announcement = True
    stored_mtime = None
    new_mtime = None
    cookie_data = {}

    if ANN_COOKIE_NAME in request.COOKIES:
        json_str = unquote(request.COOKIES[ANN_COOKIE_NAME])
        cookie_data = json.loads(json_str)

        if 'isOpen' in cookie_data:
            display_announcement = cookie_data['isOpen']

        if project.code in cookie_data:
            stored_mtime = cookie_data[project.code]

    if announcement is not None:
        ann_mtime = dateformat.format(announcement.modified_on, 'U')
        if ann_mtime != stored_mtime:
            display_announcement = True
            new_mtime = ann_mtime

    tp_goals = translation_project.all_goals

    ctx.update(get_overview_context(request))
    ctx.update({
        'resource_obj': request.store or request.directory,  # Dirty hack.
        'translation_project': translation_project,
        'description': translation_project.description,
        'project': project,
        'language': language,
        'tp_goals': tp_goals,
        'goal': goal,
        'feed_path': request.directory.pootle_path[1:],
        'action_groups': actions,
        'action_output': action_output,
        'can_edit': can_edit,

        'browser_extends': 'translation_projects/base.html',

        'announcement': announcement,
        'announcement_displayed': display_announcement,
    })

    tp_pootle_path = translation_project.pootle_path

    if request.store is None:
        table_fields = ['name', 'progress', 'total', 'need-translation',
                        'suggestions', 'critical', 'last-updated', 'activity']

        if goal is not None:
            # Then show the drill down view for the specified goal.
            continue_url = goal.get_translate_url_for_path(request.pootle_path,
                                                           state='incomplete')
            critical_url = goal.get_critical_url_for_path(request.pootle_path)
            review_url = goal.get_translate_url_for_path(request.pootle_path,
                                                         state='suggestions')
            all_url = goal.get_translate_url_for_path(request.pootle_path)

            ctx.update({
                'table': {
                    'id': 'tp-goals',
                    'fields': table_fields,
                    'headings': get_table_headings(table_fields),
                    'parent': get_goal_parent(request.directory, goal),
                    'items': get_goal_children(request.directory, goal),
                },
                'url_action_continue': continue_url,
                'url_action_fixcritical': critical_url,
                'url_action_review': review_url,
                'url_action_view_all': all_url,
            })
        else:
            # Then show the files tab.
            ctx.update({
                'table': {
                    'id': 'tp-files',
                    'fields': table_fields,
                    'headings': get_table_headings(table_fields),
                    'parent': get_parent(request.directory),
                    'items': get_children(request.directory),
                },
            })

    if can_edit:
        if request.store is None:
            add_tag_action_url = reverse('pootle-xhr-tag-tp',
                                         args=[language.code, project.code])
        else:
            add_tag_action_url = reverse('pootle-xhr-tag-store',
                                         args=[resource_obj.pk])

        ctx.update({
            'form': DescriptionForm(instance=translation_project),
            'form_action': reverse('pootle-tp-admin-settings',
                                   args=[language.code, project.code]),
            'add_tag_form': TagForm(),
            'add_tag_action_url': add_tag_action_url,
        })

        if goal is not None:
            ctx.update({
                'goal_form': GoalForm(instance=goal),
                'goal_form_action': reverse('pootle-xhr-edit-goal',
                                            args=[goal.slug]),
            })

    response = render(request, template_name, ctx)

    if new_mtime is not None:
        cookie_data[project.code] = new_mtime
        cookie_data = quote(json.dumps(cookie_data))
        response.set_cookie(ANN_COOKIE_NAME, cookie_data)

    return response


@require_POST
@ajax_required
@get_path_obj
@permission_required('administrate')
def ajax_remove_tag_from_tp(request, translation_project, tag_name):

    if tag_name.startswith("goal:"):
        translation_project.goals.remove(tag_name)
    else:
        translation_project.tags.remove(tag_name)

    return HttpResponse(status=201)


def _add_tag(request, translation_project, tag_like_object):
    if isinstance(tag_like_object, Tag):
        translation_project.tags.add(tag_like_object)
    else:
        translation_project.goals.add(tag_like_object)
    context = {
        'tp_tags': translation_project.tag_like_objects,
        'language': translation_project.language,
        'project': translation_project.project,
        'can_edit': check_permission('administrate', request),
    }
    response = render(request, "translation_projects/xhr_tags_list.html", context)
    response.status_code = 201
    return response


@require_POST
@ajax_required
@get_path_obj
@permission_required('administrate')
def ajax_add_tag_to_tp(request, translation_project):
    """Return an HTML snippet with the failed form or blank if valid."""

    add_tag_form = TagForm(request.POST)

    if add_tag_form.is_valid():
        new_tag_like_object = add_tag_form.save()
        return _add_tag(request, translation_project, new_tag_like_object)
    else:
        # If the form is invalid, perhaps it is because the tag (or goal)
        # already exists, so check if the tag (or goal) exists.
        try:
            criteria = {
                'name': add_tag_form.data['name'],
                'slug': add_tag_form.data['slug'],
            }
            if len(translation_project.tags.filter(**criteria)) == 1:
                # If the tag is already applied to the translation project then
                # avoid reloading the page.
                return HttpResponse(status=204)
            elif len(translation_project.goals.filter(**criteria)) == 1:
                # If the goal is already applied to the translation project
                # then avoid reloading the page.
                return HttpResponse(status=204)
            else:
                # Else add the tag (or goal) to the translation project.
                if criteria['name'].startswith("goal:"):
                    tag_like_object = Goal.objects.get(**criteria)
                else:
                    tag_like_object = Tag.objects.get(**criteria)
                return _add_tag(request, translation_project, tag_like_object)
        except Exception:
            # If the form is invalid and the tag (or goal) doesn't exist yet
            # then display the form with the error messages.
            url_kwargs = {
                'language_code': translation_project.language.code,
                'project_code': translation_project.project.code,
            }
            context = {
                'add_tag_form': add_tag_form,
                'add_tag_action_url': reverse('pootle-xhr-tag-tp',
                                              kwargs=url_kwargs)
            }
            return render(request, "core/xhr_add_tag_form.html", context)


@get_path_obj
@permission_required('view')
@get_resource
def translate(request, translation_project, dir_path, filename):
    language = translation_project.language
    project = translation_project.project

    is_terminology = (project.is_terminology or request.store and
                                                request.store.is_terminology)
    context = get_translation_context(request, is_terminology=is_terminology)

    context.update({
        'language': language,
        'project': project,
        'translation_project': translation_project,

        'editor_extends': 'translation_projects/base.html',
    })

    return render(request, "editor/main.html", context)


@get_path_obj
@permission_required('view')
@get_resource
def export_view(request, translation_project, dir_path, filename=None):
    """Displays a list of units with filters applied."""
    ctx = get_export_view_context(request)
    ctx.update({
        'source_language': translation_project.project.source_language,
        'language': translation_project.language,
        'project': translation_project.project,
        'goal': request.GET.get('goal', ''),
    })

    return render(request, "editor/export_view.html", ctx)


@require_POST
@ajax_required
@get_path_obj
@permission_required('administrate')
def edit_settings(request, translation_project):
    from pootle.core.url_helpers import split_pootle_path

    form = DescriptionForm(request.POST, instance=translation_project)
    response = {}
    rcode = 400

    if form.is_valid():
        form.save()
        rcode = 200

        if translation_project.description:
            response["description"] = translation_project.description
        else:
            response["description"] = (u'<p class="placeholder muted">%s</p>' %
                                       _(u"No description yet."))

    path_args = split_pootle_path(translation_project.pootle_path)[:2]
    context = {
        "form": form,
        "form_action": reverse('pootle-tp-admin-settings', args=path_args),
    }
    t = loader.get_template('admin/_settings_form.html')
    c = RequestContext(request, context)
    response['form'] = t.render(c)

    return HttpResponse(jsonify(response), status=rcode,
                        mimetype="application/json")
