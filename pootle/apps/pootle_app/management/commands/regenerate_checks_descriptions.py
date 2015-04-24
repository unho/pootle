#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import logging
import os

# This must be run before importing Django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'pootle.settings'

from django.core.management.base import NoArgsCommand

from pootle.core.initdb import create_quality_checks_descriptions
from staticpages.models import StaticPage


class Command(NoArgsCommand):
    help = 'Regenerates the quality checks descriptions.'

    def handle_noargs(self, **options):
        logging.info('Regenerating quality checks descriptions.')
        StaticPage.objects.filter(virtual_path="help/quality-checks").delete()
        create_quality_checks_descriptions()
        logging.info('Successfully regenerated quality checks descriptions.')
