# $Id$
#
# Copyright (C) 2011  Internet Systems Consortium ("ISC")
# 
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND ISC DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS.  IN NO EVENT SHALL ISC BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
# OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

from distutils.core import setup, Extension
import os

# We can't build POW without these settings, but allow them to be null
# so that things like "python setup.py --help" will work.

ac_cflags	= os.getenv("AC_CFLAGS",	"").split()
ac_ldflags	= os.getenv("AC_LDFLAGS",	"").split()
ac_libs		= os.getenv("AC_LIBS",		"").split()
ac_scripts	= os.getenv("AC_SCRIPTS",	"").split()
ac_aux_scripts  = os.getenv("AC_AUX_SCRIPTS",   "").split()

ac_sbindir	= os.getenv("AC_SBINDIR",	"").strip()
ac_abs_builddir = os.getenv("AC_ABS_BUILDDIR",	"").strip()
ac_libexecdir   = os.getenv("AC_LIBEXECDIR",    "").strip()

# Non-standard extension build specification: we need to force
# whatever build options our top-level ./configure selected, and we
# have to specify our libraries as extra_link_args because they may be
# complete pathnames to .a files elsewhere in the build tree.  Most of
# this insanity is to kludge around pre-existing OpenSSL libraries
# that would screw up our build without these gymnastics.

pow = Extension("rpki.POW._POW", ["ext/POW.c"], 
                extra_compile_args = ac_cflags,
                extra_link_args    = ac_ldflags + ac_libs)

# Be careful constructing data_files, empty file lists here appear to
# confuse setup into putting dangerous nonsense into the list of
# installed files.
#
# bdist_rpm seems to get confused by relative names for scripts, so we
# have to prefix source names here with the build directory name.

data_files = []
if ac_sbindir and ac_scripts:
  data_files.append((ac_sbindir,
                     ["%s/%s" % (ac_abs_builddir, f) for f in ac_scripts]))
if ac_libexecdir and ac_aux_scripts:
  data_files.append((ac_libexecdir,
                     ["%s/%s" % (ac_abs_builddir, f) for f in ac_aux_scripts]))
if not data_files:
  data_files = None

setup(name              = "rpkitoolkit",
      version           = "1.0",
      description       = "RPKI Toolkit",
      license           = "BSD",
      url               = "http://www.rpki.net/",
      packages          = ["rpki", "rpki.POW", "rpki.gui", "rpki.gui.app", "rpki.gui.cacheview" ],
      ext_modules       = [pow],
      package_data      = { 'rpki.gui.app' : ['templates/*.html', 'templates/*/*.html'],
                            'rpki.gui.cacheview' : [ 'templates/*/*.html' ] },
      data_files	= data_files)
