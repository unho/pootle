#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2008-2014 Zuza Software Foundation
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

import logging
import os
from StringIO import StringIO

from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.utils.encoding import iri_to_uri
from django.utils.translation import ugettext as _

from pootle.core.decorators import get_path_obj, permission_required
from pootle_app.models import Directory
from pootle_app.models.permissions import check_permission
from pootle_app.project_tree import (direct_language_match_filename,
                                     ensure_target_dir_exists)
from pootle_statistics.models import Submission, SubmissionTypes
from pootle_store.decorators import get_store_context
from pootle_store.models import Store
from pootle_store.util import absolute_real_path, relative_real_path

from .forms import upload_form_factory
from .signals import post_file_upload


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


def _host_to_unix_path(p):
    return '/'.join(p.split(os.sep))


def _get_upload_path(translation_project, relative_root_dir, local_filename):
    """Get the path of a translation file being uploaded securely, creating
    directories as necessary.
    """
    unix_to_host_path = os.sep.join(relative_root_dir.split('/'))
    dir_path = os.path.join(translation_project.real_path, unix_to_host_path)
    return relative_real_path(os.path.join(dir_path, local_filename))


def _get_local_filename(translation_project, upload_filename):
    base, ext = os.path.splitext(upload_filename)
    new_ext = translation_project.project.localfiletype

    if new_ext == 'po' and translation_project.is_template_project:
        new_ext = 'pot'

    local_filename = '%s.%s' % (base, new_ext)

    # Check if name is valid.
    if (os.path.basename(local_filename) != local_filename or
        local_filename.startswith(".")):
        raise ValueError(_("Invalid/insecure file name: %s", local_filename))

    # XXX: Leakage of the project layout information outside of
    # project_tree.py! The rest of Pootle shouldn't have to care
    # whether something is GNU-style or not.
    if (translation_project.file_style == "gnu" and
        not translation_project.is_template_project):

        language_code = translation_project.language.code
        if not direct_language_match_filename(language_code, local_filename):
            invalid_dict = {
                'local_filename': local_filename,
                'langcode': translation_project.language.code,
                'filetype': translation_project.project.localfiletype,
            }
            raise ValueError(_("Invalid GNU-style file name: "
                               "%(local_filename)s. It must match "
                               "'%(langcode)s.%(filetype)s'.", invalid_dict))
    return local_filename


def _unzip_external(request, directory, django_file, overwrite):
    # Make a temporary directory to hold a zip file and its unzipped contents.
    from pootle_misc import ptempfile as tempfile

    tempdir = tempfile.mkdtemp(prefix='pootle')

    # Make a temporary file to hold the zip file.
    tempzipfd, tempzipname = tempfile.mkstemp(prefix='pootle', suffix='.zip')
    try:
        # Dump the uploaded file to the temporary file.
        try:
            os.write(tempzipfd, django_file.read())
        finally:
            os.close(tempzipfd)

        # Unzip the temporary zip file.
        import subprocess
        if subprocess.call(["unzip", tempzipname, "-d", tempdir]):
            import zipfile
            raise zipfile.BadZipfile(_("Error while extracting archive"))

        # Enumerate the temporary directory.
        maybe_skip = True
        prefix = tempdir
        for basedir, dirs, files in os.walk(tempdir):
            if maybe_skip and not files and len(dirs) == 1:
                try:
                    directory.child_dirs.get(name=dirs[0])
                    maybe_skip = False
                except Directory.DoesNotExist:
                    prefix = os.path.join(basedir, dirs[0])
                    continue
            else:
                maybe_skip = False

            for fname in files:
                # Read the contents of a file.
                fcontents = open(os.path.join(basedir, fname), 'rb').read()
                newfile = StringIO(fcontents)
                newfile.name = os.path.basename(fname)

                # Get the filesystem path relative to the temporary directory.
                subdir = _host_to_unix_path(basedir[len(prefix)+len(os.sep):])
                if subdir:
                    target_dir = directory.get_or_make_subdir(subdir)
                else:
                    target_dir = directory

                # Construct a full UNIX path relative to the current
                # translation project URL by attaching a UNIXified
                # 'relative_host_dir' to the root relative path, i.e. the path
                # from which the user is uploading the ZIP file.
                try:
                    _upload_file(request, target_dir, newfile, overwrite)
                except ValueError:
                    logging.exception(u"Error adding file %s", fname)
    finally:
        # Clean up temporary file and directory used in try-block.
        import shutil
        os.unlink(tempzipname)
        shutil.rmtree(tempdir)


def _unzip_python(request, directory, django_file, overwrite):
    import zipfile

    django_file.seek(0)
    archive = zipfile.ZipFile(django_file, 'r')
    # TODO: find a better way to return errors...
    try:
        prefix = ''
        maybe_skip = True
        for filename in archive.namelist():
            try:
                if filename[-1] == '/':
                    if maybe_skip:
                        try:
                            directory.child_dirs.get(name=filename[:-1])
                            maybe_skip = False
                        except Directory.DoesNotExist:
                            prefix = filename
                else:
                    maybe_skip = False
                    subdir = _host_to_unix_path(os.path.dirname(filename[len(prefix):]))
                    if subdir:
                        target_dir = directory.get_or_make_subdir(subdir)
                    else:
                        target_dir = directory
                    newfile = StringIO(archive.read(filename))
                    newfile.name = os.path.basename(filename)
                    _upload_file(request, target_dir, newfile, overwrite)
            except ValueError:
                logging.exception(u"Error adding file %s", filename)
    finally:
        archive.close()


def _upload_archive(request, directory, django_file, overwrite):
    # First we try to use "unzip" from the system, otherwise fall back to using
    # the slower zipfile module.
    try:
        _unzip_external(request, directory, django_file, overwrite)
    except:
        _unzip_python(request, directory, django_file, overwrite)


def _overwrite_file(request, relative_root_dir, django_file, upload_path):
    """Overwrite with uploaded file."""
    upload_dir = os.path.dirname(absolute_real_path(upload_path))
    # Ensure that there is a directory into which we can dump the uploaded
    # file.
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    # Get the file extensions of the uploaded filename and the current
    # translation project.
    _upload_base, upload_ext = os.path.splitext(django_file.name)
    _local_base, local_ext = os.path.splitext(upload_path)
    # If the extension of the uploaded file matches the extension used in this
    # translation project, then we simply write the file to the disk.
    if upload_ext == local_ext:
        outfile = open(absolute_real_path(upload_path), "wb")
        try:
            outfile.write(django_file.read())
        finally:
            outfile.close()
            try:
                #FIXME: we need a way to delay reparsing
                store = Store.objects.get(file=upload_path)
                store.update(update_structure=True, update_translation=True)
            except Store.DoesNotExist:
                # newfile, delay parsing
                pass
    else:
        from translate.storage import factory
        from pootle_store.filetypes import factory_classes

        newstore = factory.getobject(django_file, classes=factory_classes)
        if not newstore.units:
            return

        # If the extension of the uploaded file does not match the extension of
        # the current translation project, we create an empty file (with the
        # right extension).
        empty_store = factory.getobject(absolute_real_path(upload_path),
                                        classes=factory_classes)
        # And save it.
        empty_store.save()
        request.translation_project.scan_files(vcs_sync=False)
        # Then we open this newly created file and merge the uploaded file into
        # it.
        store = Store.objects.get(file=upload_path)
        #FIXME: maybe there is a faster way to do this?
        store.update(update_structure=True, update_translation=True,
                     store=newstore)
        store.sync(update_structure=True, update_translation=True,
                   conservative=False)


def _upload_file(request, directory, django_file, overwrite, store=None):
    from django.core.exceptions import PermissionDenied
    from translate.storage import factory
    from pootle_store.filetypes import factory_classes

    translation_project = request.translation_project
    tp_pootle_path_length = len(translation_project.pootle_path)
    relative_root_dir = directory.pootle_path[tp_pootle_path_length:]

    # for some reason factory checks explicitly for file existance and
    # if file is open, which makes it difficult to work with Django's
    # in memory uploads.
    #
    # setting _closed to False should work around this
    #FIXME: hackish, does this have any undesirable side effect?
    if getattr(django_file, '_closed', None) is None:
        try:
            django_file._closed = False
        except AttributeError:
            pass
    # factory also checks for _mode
    if getattr(django_file, '_mode', None) is None:
        try:
            django_file._mode = 1
        except AttributeError:
            pass
    # mode is an attribute not a property in Django 1.1
    if getattr(django_file, 'mode', None) is None:
        django_file.mode = 1

    if store and store.file:
        # Uploading to an existing file.
        pootle_path = store.pootle_path
        upload_path = store.real_path
    elif store:
        # Uploading to a virtual store.
        pootle_path = store.pootle_path
        upload_path = _get_upload_path(translation_project, relative_root_dir,
                                       store.name)
    else:
        local_filename = _get_local_filename(translation_project,
                                             django_file.name)
        pootle_path = directory.pootle_path + local_filename
        # The full filesystem path to 'local_filename'.
        upload_path = _get_upload_path(translation_project, relative_root_dir,
                                       local_filename)
        try:
            store = translation_project.stores.get(pootle_path=pootle_path)
        except Store.DoesNotExist:
            store = None

    if (store is not None and overwrite == 'overwrite' and
        not check_permission('overwrite', request)):
        raise PermissionDenied(_("You do not have rights to overwrite files "
                                 "here."))

    if store is None and not check_permission('administrate', request):
        raise PermissionDenied(_("You do not have rights to upload new files "
                                 "here."))

    if overwrite == 'merge' and not check_permission('translate', request):
        raise PermissionDenied(_("You do not have rights to upload files "
                                 "here."))

    if overwrite == 'suggest' and not check_permission('suggest', request):
        raise PermissionDenied(_("You do not have rights to upload files "
                                 "here."))

    if store is None or (overwrite == 'overwrite' and store.file != ""):
        _overwrite_file(request, relative_root_dir, django_file, upload_path)
        return

    if store.file and store.file.read() == django_file.read():
        logging.debug(u"identical file uploaded to %s, not merging",
                      store.pootle_path)
        return

    django_file.seek(0)
    newstore = factory.getobject(django_file, classes=factory_classes)

    #FIXME: are we sure this is what we want to do? shouldn't we
    # differentiate between structure changing uploads and mere
    # pretranslate uploads?
    suggestions = overwrite == 'merge'
    notranslate = overwrite == 'suggest'
    allownewstrings = overwrite == 'overwrite' and store.file == ''

    store.mergefile(newstore, request.user, suggestions=suggestions,
                    notranslate=notranslate,
                    allownewstrings=allownewstrings,
                    obsoletemissing=allownewstrings)


def handle_upload_form(request, translation_project):
    """Process the upload form in TP overview."""
    upload_form_class = upload_form_factory(request)

    if request.method == 'POST' and 'file' in request.FILES:
        upload_form = upload_form_class(request.POST, request.FILES)

        if not upload_form.is_valid():
            return upload_form
        else:
            django_file = upload_form.cleaned_data['file']
            overwrite = upload_form.cleaned_data['overwrite']
            upload_to = upload_form.cleaned_data['upload_to']
            upload_to_dir = upload_form.cleaned_data['upload_to_dir']

            # XXX Why do we scan here?
            translation_project.scan_files(vcs_sync=False)
            oldstats = translation_project.get_stats()

            # The URL relative to the URL of the translation project. Thus, if
            # directory.pootle_path == /af/pootle/foo/bar, then
            # relative_root_dir == foo/bar.
            if django_file.name.endswith('.zip'):
                archive = True
                target_directory = upload_to_dir or request.directory
                _upload_archive(request, target_directory, django_file,
                                overwrite)
            else:
                archive = False
                _upload_file(request, request.directory, django_file,
                             overwrite, store=upload_to)

            translation_project.scan_files(vcs_sync=False)
            newstats = translation_project.get_stats()

            # Create a submission. Doesn't fix stats but at least shows up in
            # last activity column.
            from django.utils import timezone
            s = Submission(
                creation_time=timezone.now(),
                translation_project=translation_project,
                submitter=request.user,
                type=SubmissionTypes.UPLOAD,
                # The other fields are only relevant to unit-based changes.
            )
            s.save()

            post_file_upload.send(sender=translation_project,
                                  user=request.user, oldstats=oldstats,
                                  newstats=newstats, archive=archive)

    # Always return a blank upload form unless the upload form is not valid.
    return upload_form_class()
