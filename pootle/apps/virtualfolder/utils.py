# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from fnmatch import fnmatch

from pootle.core.url_helpers import split_pootle_path
from pootle_fs.utils import PathFilter
from pootle_store.models import Store

from .models import VirtualFolder, VirtualFolderTreeItem


def update_vfolder_tree(vf, store):
    """For a given VirtualFolder and Store update the VirtualFolderTreeItem
    """
    # Create missing VirtualFolderTreeItem tree structure for affected Stores
    # after adding or unobsoleting Units.
    created = False
    try:
        vfolder_treeitem = (
            VirtualFolderTreeItem.objects.select_related("directory").get(
                directory=store.parent, vfolder=vf))
    except VirtualFolderTreeItem.DoesNotExist:
        parts = split_pootle_path(store.parent.pootle_path)
        path_parts = ["", parts[0], parts[1], vf.name]
        if parts[2]:
            path_parts.append(parts[2].strip("/"))
        path_parts.append(parts[3])
        pootle_path = "/".join(path_parts)
        vfolder_treeitem = (
            VirtualFolderTreeItem.objects.create(
                pootle_path=pootle_path,
                directory=store.parent,
                vfolder=vf))
        created = True
    if not created:
        # The VirtualFolderTreeItem already existed, so
        # calculate again the stats up to the root.
        vfolder_treeitem.update_all_cache()


class VirtualFolderFinder(object):
    """Find vfs for a new store"""

    def __init__(self, store):
        self.store = store

    @property
    def language(self):
        return self.store.translation_project.language

    @property
    def project(self):
        return self.store.translation_project.project

    @property
    def possible_vfolders(self):
        return (
            self.project.vfolders.filter(all_languages=True)
            | self.language.vfolders.filter(all_projects=True)
            | self.project.vfolders.filter(languages=self.language)
            | VirtualFolder.objects.filter(
                all_languages=True, all_projects=True))

    def add_to_vfolders(self):
        to_add = []
        for vf in self.possible_vfolders:
            if vf.path_matcher.should_add_store(self.store):
                to_add.append(vf)
        if to_add:
            self.store.vfolders.add(*to_add)
            self.store.set_priority()
        for vf in to_add:
            update_vfolder_tree(vf, self.store)


class VirtualFolderPathMatcher(object):

    tp_path = "/[^/]*/[^/]*/"

    def __init__(self, vf):
        self.vf = vf

    @property
    def existing_stores(self):
        """Currently associated Stores"""
        return self.vf.stores.all()

    @property
    def languages(self):
        """The languages associated with this vfolder
        If `all_languages` is set then `None` is returned
        """
        if self.vf.all_languages:
            return None
        return self.vf.languages.values_list("pk", flat=True)

    @property
    def projects(self):
        """The projects associated with this vfolder
        If `all_projects` is set then `None` is returned
        """
        if self.vf.all_projects:
            return None
        return self.vf.projects.values_list("pk", flat=True)

    @property
    def matching_stores(self):
        """Store qs containing all stores that match
        project, language, and rules for this vfolder
        """
        return self.filter_from_rules(self.store_qs)

    @property
    def rules(self):
        """Glob matching rules"""
        return (
            "%s" % r.strip()
            for r
            in self.vf.filter_rules.split(","))

    @property
    def store_manager(self):
        """The root object manager for finding/adding stores"""
        return Store.objects

    @property
    def store_qs(self):
        """The stores qs without any rule filtering"""
        return self.filter_projects(
            self.filter_languages(
                self.store_manager))

    def add_and_remove_stores(self):
        """Add Stores that should be associated but arent, delete Store
        associations for Stores that are associated but shouldnt be
        """
        existing_stores = set(self.existing_stores)
        matching_stores = set(self.matching_stores)
        to_add = matching_stores - existing_stores
        to_remove = existing_stores - matching_stores
        if to_add:
            self.add_stores(to_add)
        if to_remove:
            self.remove_stores(to_remove)
        return to_add, to_remove

    def add_stores(self, stores):
        """Associate a Store"""
        self.vf.stores.add(*stores)

    def filter_from_rules(self, qs):
        filtered_qs = qs.none()
        for rule in self.rules:
            filtered_qs = (
                filtered_qs
                | qs.filter(pootle_path__regex=self.get_rule_regex(rule)))
        return filtered_qs

    def filter_languages(self, qs):
        if self.languages is None:
            return qs
        return qs.filter(
            translation_project__language_id__in=self.languages)

    def filter_projects(self, qs):
        if self.projects is None:
            return qs
        return qs.filter(
            translation_project__project_id__in=self.projects)

    def get_rule_regex(self, rule):
        """For a given *glob* rule, return a pootle_path *regex*"""
        return (
            "^%s%s"
            % (self.tp_path,
               PathFilter().path_regex(rule)))

    def path_matches(self, path):
        """Returns bool of whether path is valid for this VF.
        """
        for rule in self.rules:
            if fnmatch(rule, path):
                return True
        return False

    def remove_stores(self, stores):
        self.vf.stores.remove(*stores)

    def should_add_store(self, store):
        if self.store_matches(store) and not self.store_associated(store):
            return True
        return False

    def store_associated(self, store):
        return self.vf.stores.through.objects.filter(
            store_id=store.id,
            virtualfolder_id=self.vf.id).exists()

    def store_matches(self, store):
        return self.path_matches(
            "".join(split_pootle_path(store.pootle_path)[2:]))

    def update_stores(self):
        """Add and delete Store associations as necessary, and set the
        priority for any affected Stores
        """
        added, removed = self.add_and_remove_stores()
        for store in added:
            update_vfolder_tree(self.vf, store)
            if store.priority != self.vf.priority:
                store.set_priority()
        for store in removed:
            if store.priority == self.vf.priority:
                store.set_priority()
