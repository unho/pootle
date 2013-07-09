#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2009-2013 Zuza Software Foundation
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

import os

from django.contrib.auth.models import User
from django.core.management.base import NoArgsCommand
from django.db import transaction


os.environ['DJANGO_SETTINGS_MODULE'] = 'pootle.settings'


class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        create_default_db()


def create_default_db():
    """This creates the default database to get a working Pootle installation.

    You can tweak the methods called or their implementation elsewhere in the
    file. This provides some sane default to get things working.
    """
    try:
        transaction.enter_transaction_management()
        transaction.managed(True)

        create_default_projects()
        create_default_languages()
        create_default_admin()
        create_default_flags()
    except:
        if transaction.is_dirty():
            transaction.rollback()
        raise
    finally:
        if transaction.is_managed():
            if transaction.is_dirty():
                transaction.commit()
            transaction.leave_transaction_management()


def create_default_projects():
    """Create the default projects that we host.

    You might want to add your projects here, although you can also add things
    through the web interface later.
    """
    from pootle_app.management import require_english
    from pootle_project.models import Project

    en = require_english()

    #pootle = Project(code=u"pootle", source_language=en)
    #pootle.fullname = u"Pootle"
    #pootle.description = ('<div dir="ltr" lang="en">Interface translations '
    #                      'for Pootle. <br /> See the <a href="http://'
    #                      'pootle.locamotion.org">official Pootle server</a> '
    #                      'for the translations of Pootle.</div>')
    #pootle.checkstyle = "standard"
    #pootle.localfiletype = "po"
    #pootle.treestyle = "auto"
    #pootle.save()

    tutorial = Project(code=u"tutorial", source_language=en)
    tutorial.fullname = u"Tutorial"
    tutorial.description = ('<div dir="ltr" lang="en">Tutorial project where '
                            'users can play with Pootle and learn more about '
                            'translation and localisation.<br />For more help '
                            'on localisation, visit the <a href="http://'
                            'translate.sourceforge.net/wiki/guide/start">'
                            'localisation guide</a>.</div>')
    tutorial.checkstyle = "standard"
    tutorial.localfiletype = "po"
    tutorial.treestyle = "auto"
    tutorial.save()


def create_default_languages():
    """Create the default languages.

    We afford this privilege to languages with reasonably complete interface
    translations for Pootle.
    """
    from translate.lang import data, factory

    from pootle_language.models import Language

    default_languages = ("af", "ak", "ht", "nso", "ve", "wo", "zh_cn",
            "zh_hk", "zh_tw", "ca_valencia", "son", "lg", "gd")

    # import languages from toolkit
    for code in data.languages.keys():
        try:
            tk_lang = factory.getlanguage(code)
            criteria = {
                'code': code,
                'fullname': tk_lang.fullname,
                'nplurals': tk_lang.nplurals,
                'pluralequation': tk_lang.pluralequation,
                'specialchars': tk_lang.specialchars,
            }
            lang, created = Language.objects.get_or_create(**criteria)
            if code in default_languages:
                lang.save()
        except:
            pass


def create_default_admin():
    """Create the default user(s) for Pootle.

    You definitely want to change the admin account so that your default
    install is not accessible with the default credentials. The users 'noboby'
    and 'default' should be left as is.
    """
    admin = User(username=u"admin",
                 first_name=u"Administrator",
                 is_active=True,
                 is_superuser=True,
                 is_staff=True,
    )
    admin.set_password("admin")
    admin.save()


def create_default_flags():
    """Create the default flags for enable or disable features in Pootle.

    Created flags are not tied to any user nor have set any other field out of
    the basic ones. If you want to use this flags you will have to to tie them
    to any existin user or alter any of its other fields. To do so go to the
    features tab in the admin panel.
    """
    from waffle.models import Flag

    sample_flag = Flag(name=u"sample_flag",
                       superusers=False,
                       note="Sample flag for enabling an action.",
    )
    sample_flag.save()
