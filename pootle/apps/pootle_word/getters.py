# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

from pootle.core.delegate import stemmer
from pootle.core.plugin import getter

from stemming.porter2 import stem


@getter(stemmer)
def get_stemmer(**kwargs_):
    return stem
