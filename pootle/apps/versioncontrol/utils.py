# -*- coding: utf-8 -*-
#
# Copyright 2012 Zuza Software Foundation
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

"""Utility functions to help with version control systems."""

import os
import shutil

from translate.storage import versioncontrol

from django.conf import settings

from pootle_app.project_tree import is_hidden_file, to_podir_path
from pootle_store.util import add_trailing_slash, relative_real_path


class VersionControlError(Exception):
    pass


def to_vcs_path(path):
    # FIXME: this is ignoring symlinks!
    path = relative_real_path(path)
    return os.path.join(settings.VCS_DIRECTORY, path)


def hasversioning(path):
    path = to_vcs_path(path)
    return versioncontrol.hasversioning(path, settings.VCS_DIRECTORY)


def commit_file(path, message, author):
    vcs_path = to_vcs_path(path)
    path = to_podir_path(path)
    shutil.copy2(path, vcs_path)
    versioncontrol.commitfile(vcs_path, message=message, author=author)


def copy_to_podir(path):
    """Copy the given path from the VCS directory to the PO directory."""
    vcs_path = to_vcs_path(path)
    path = to_podir_path(path)
    shutil.copy2(vcs_path, path)


def update_file(path):
    vcs_path = to_vcs_path(path)
    path = to_podir_path(path)
    versioncontrol.updatefile(vcs_path)
    shutil.copy2(vcs_path, path)


def update_dir(path):
    """Updates a whole directory without syncing with the po directory.

    This assumes that we can update cleanly, and must be followed by
    :meth:`~pootle_translationproject.models.TranslationProject.scan_files`
    since the podirectory isn't updated as part of this call.

    For some systems (like git) this can cause the rest of a cloned repository
    to be updated as well, so changes might not be limited to the given path.
    """
    vcs_path = to_vcs_path(path)
    vcs_object = versioncontrol.get_versioned_object(vcs_path)
    vcs_object.update(needs_revert=False)


def add_files(path, files, message, author=None):
    vcs_path = to_vcs_path(path)
    path = to_podir_path(path)
    vcs = versioncontrol.get_versioned_object(vcs_path)
    #: list of (podir_path, vcs_path) tuples
    file_paths = [(to_podir_path(f), to_vcs_path(f)) for f in files]
    for podir_path, vcs_path in file_paths:
        vcs_dir = os.path.dirname(vcs_path)
        if not os.path.exists(vcs_dir):
            os.makedirs(vcs_dir)
        shutil.copy(podir_path, vcs_path)
    output = vcs.add([to_vcs_path(f) for f in files], message, author)
    return output


def recursive_files_and_dirs(ignored_files, ext, real_dir, file_filter):
    """Traverses :param:`real_dir` searching for files and directories.

    :param ignored_files: List of files that will be ignored.
    :param ext: Only files ending with this extension will be considered.
    :param real_dir:
    :param file_filter: Filtering function applied to the list of files found.
    :return: A tuple of lists of files and directories found when traversing the
        given path and after applying the given restrictions.
    """
    real_dir = add_trailing_slash(real_dir)
    files = []
    dirs = []

    for _path, _dirs, _files in os.walk(real_dir, followlinks=True):
        # Make it relative:
        _path = _path[len(real_dir):]
        files += [os.path.join(_path, f) for f in filter(file_filter, _files)
                  if f.endswith(ext) and f not in ignored_files]

        # Edit _dirs in place to avoid further recursion into hidden directories
        for d in _dirs:
            if is_hidden_file(d):
                _dirs.remove(d)

        dirs += _dirs

    return files, dirs


def sync_from_vcs(ignored_files, ext, relative_dir,
                  file_filter=lambda _x: True):
    """Recursively synchronise the PO directory from the VCS directory.

    This brings over files from VCS, and removes files in PO directory that
    were removed in VCS.
    """
    if not hasversioning(relative_dir):
        return

    podir_path = to_podir_path(relative_dir)
    vcs_path = to_vcs_path(relative_dir)
    vcs_files, vcs_dirs = recursive_files_and_dirs(ignored_files, ext,
                                                   vcs_path, file_filter)
    files, dirs = recursive_files_and_dirs(ignored_files, ext, podir_path,
                                           file_filter)

    vcs_file_set = set(vcs_files)
    vcs_dir_set = set(vcs_dirs)
    file_set = set(files)
    dir_set = set(dirs)

    for d in vcs_dir_set - dir_set:
        new_path = os.path.join(podir_path, d)
        os.makedirs(new_path)

    # copy into podir
    for f in vcs_file_set - file_set:
        vcs_f = os.path.join(vcs_path, f)
        new_path = os.path.join(podir_path, f)
        shutil.copy2(vcs_f, new_path)

    # remove from podir
    #TODO: review this carefully, as we are now deleting stuff
    for f in file_set - vcs_file_set:
        remove_path = os.path.join(podir_path, f)
        os.remove(remove_path)

    for d in dir_set - vcs_dir_set:
        remove_path = os.path.join(podir_path, d)
        shutil.rmtree(remove_path)
