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

"""Signal handlers for generating automatic notifications on system events."""

import logging

from pootle_autonotices.signals import new_object
from pootle_misc.stats import stats_message_raw


def file_uploaded(sender, oldstats, user, newstats, archive, **kwargs):
    if sender.is_template_project:
        # Add template news to project instead of translation project.
        directory = sender.project.directory
    else:
        directory = sender.directory

    if oldstats == newstats:
        logging.debug("file uploaded but stats didn't change")
        return

    args = {
        'user_url': user.get_absolute_url(),
        'user': user,
        'sender_url': sender.get_absolute_url(),
        'sender': sender.fullname,
    }
    if archive:
        message = ('<a href="%(user_url)s">%(user)s</a> uploaded an archive '
                   'to <a href="%(sender_url)s">%(sender)s</a> <br />' % args)
    else:
        message = ('<a href="%(user_url)s">%(user)s</a> uploaded a file to '
                   '<a href="%(sender_url)s">%(sender)s</a> <br />' % args)

    old_total = oldstats["total"]
    new_total = newstats["total"]
    old_translated = oldstats["translated"]
    new_translated = newstats["translated"]
    old_fuzzy = oldstats["fuzzy"]
    new_fuzzy = newstats["fuzzy"]
    message += stats_message_raw('Before upload', old_total, old_translated,
                                 old_fuzzy) + ' <br />'
    message += stats_message_raw('After upload', new_total, new_translated,
                                 new_fuzzy) + ' <br />'
    new_object(True, message, directory)
