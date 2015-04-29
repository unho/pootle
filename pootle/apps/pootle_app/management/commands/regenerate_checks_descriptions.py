#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import codecs
import logging
import os

from translate.filters.checks import TeeChecker

# This must be run before importing Django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'pootle.settings'

from django.core.management.base import CommandError, NoArgsCommand

from pootle_misc.checks import check_names, excluded_filters
from staticpages.models import StaticPage


def create_checks_descriptions():
    """Create the descriptions for all the quality checks."""
    try:
        from docutils.core import publish_parts
    except ImportError:
        raise CommandError("Please install missing 'docutils' dependency.")

    # First get Evernote quality checks descriptions.
    filename = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            '../../../../templates/checks/descriptions.html')

    with codecs.open(filename, 'r', 'utf-8') as f:
        body = f.read()

    # Now get Translate Toolkit quality checks descriptions.

    def get_check_description(name, filterfunc):
        # Provide a header with an anchor to refer to.
        description = ('\n<h3 id="%s">%s</h3>\n\n' %
                       (name, unicode(check_names[name])))

        # Clean the leading whitespace on each docstring line so it gets
        # properly rendered.
        docstring = '\n'.join([line.strip()
                               for line in filterfunc.__doc__.split('\n')])

        # Render the reStructuredText in the docstring into HTML.
        description += publish_parts(docstring, writer_name='html')['body']
        return description

    filterdict = TeeChecker().getfilters(excludefilters=excluded_filters)

    filterdocs = [get_check_description(name, filterfunc)
                  for (name, filterfunc) in filterdict.iteritems()]

    filterdocs.sort()

    body += u"\n".join(filterdocs)

    # Finally save the quality checks descriptions in a staticpage.
    checks_page = StaticPage(active=True, title="Quality Checks", body=body,
                             virtual_path="help/quality-checks")
    checks_page.save()


class Command(NoArgsCommand):
    help = 'Regenerates the quality checks descriptions.'

    def handle_noargs(self, **options):
        logging.info('Regenerating quality checks descriptions.')
        StaticPage.objects.filter(virtual_path="help/quality-checks").delete()
        create_checks_descriptions()
        logging.info('Successfully regenerated quality checks descriptions.')
