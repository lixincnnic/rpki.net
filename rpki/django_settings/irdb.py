# $Id$

# Copyright (C) 2014  Dragon Research Labs ("DRL")
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND DRL DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS.  IN NO EVENT SHALL DRL BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
# OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

"""
This module contains configuration settings for Django libraries.  All
of the back-end programs (rpkic, irdbd, etc) use this configuration;
the GUI code also uses this but adds a bunch of other stuff, thus has
its own settings file.
"""

from .common import *

__version__ = "$Id$"


# Database configuration.

DATABASES = dict(
    default = dict(ENGINE   = "django.db.backends.mysql",
                   NAME     = cfg.get("sql-database", section = "irdbd"),
                   USER     = cfg.get("sql-username", section = "irdbd"),
                   PASSWORD = cfg.get("sql-password", section = "irdbd")))

# Apps.

INSTALLED_APPS = ["rpki.irdb"]


# Allow local site to override any setting above -- but if there's
# anything that local sites routinely need to modify, please consider
# putting that configuration into rpki.conf and just adding code here
# to read that configuration.
try:
    from local_settings import *
except:
    pass