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


def directory(fn):
    """Decorator that returns links only for directory objects."""
    def wrapper(request, path_obj, **kwargs):
        if not path_obj.is_dir:
            return

        return fn(request, path_obj)

    return wrapper


def store(fn):
    """Decorator that returns links only for store objects."""
    def wrapper(request, path_obj, **kwargs):
        if path_obj.is_dir:
            return

        return fn(request, path_obj)

    return wrapper
