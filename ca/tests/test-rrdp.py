#!/usr/bin/env python
# $Id$
#
# Copyright (C) 2013  Dragon Research Labs ("DRL")
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
Proof-of-concept test driver for RRDP code.  Still fairly kludgy in places.
"""

import os
import sys
import glob
import time
import signal
import textwrap
import argparse
import subprocess

parser = argparse.ArgumentParser(description = __doc__)
parser.add_argument("--use-smoketest", action = "store_true")
parser.add_argument("--yaml-file", default = "smoketest.2.yaml")
parser.add_argument("--delay", type = int, default = 30)
parser.add_argument("--exhaustive", action = "store_true")
parser.add_argument("--skip-daemons", action = "store_true")
parser.add_argument("--dry-run", action = "store_true")
args = parser.parse_args()

def log(msg):
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()

def run(*argv):
    log("Running: " + " ".join(argv))
    if not args.dry_run:
        subprocess.check_call(argv)

def dataglob(pattern):
    return glob.iglob(os.path.join(("smoketest.dir" if args.use_smoketest else "yamltest.dir/RIR"), pattern))

def snapshot_to_serial(fn):
    return int(os.path.splitext(os.path.basename(fn))[0])

def delta_to_serial(fn):
    return int(os.path.splitext(os.path.basename(fn))[0])

top = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), "..", ".."))

rrdp_test_tool = os.path.join(top, "potpourri/rrdp-test-tool")
rcynic         = os.path.join(top, "rp/rcynic/rcynic")
rcynic_text    = os.path.join(top, "rp/rcynic/rcynic-text")

with open("rcynic-rrdp.conf", "w") as f:
    f.write(textwrap.dedent('''# Automatically generated for RRDP tests, do not edit.
      [rcynic]
      xml-summary  = rcynic.xml
      jitter       = 0
      use-links    = yes
      use-syslog   = no
      use-stderr   = yes
      log-level    = log_debug
      run-rsync    = no
      '''))
    if args.use_smoketest:
        f.write("trust-anchor = smoketest.dir/root.cer\n")
    else:
        f.write("trust-anchor = yamltest.dir/RIR/publication/RIR-root/root.cer\n")

if args.skip_daemons:
    log("--skip-daemons specified, so running neither smoketest nor yamltest")
elif args.use_smoketest:
    run("python", "smoketest.py", args.yaml_file)
else:
    run("python", "sql-cleaner.py")
    class GotSIGUSR1(Exception):
        pass
    def handle_sigusr1(signum, frame):
        raise GotSIGUSR1
    old_sigusr1 = signal.signal(signal.SIGUSR1, handle_sigusr1)
    cmd = ("python", "yamltest.py", args.yaml_file, "--notify-when-startup-complete", str(os.getpid()))
    log("Running: " + " ".join(cmd))
    yamltest = subprocess.Popen(cmd)
    log("Waiting for SIGUSR1 from yamltest")
    try:
        while True:
            signal.pause()
    except GotSIGUSR1:
        signal.signal(signal.SIGUSR1, old_sigusr1)
    log("Sleeping %s" % args.delay)
    time.sleep(args.delay)
    yamltest.terminate()

snapshots = dict((snapshot_to_serial(fn), fn) for fn in dataglob("rrdp-publication/*/snapshot/*.xml"))
deltas    = dict((delta_to_serial(fn),    fn) for fn in dataglob("rrdp-publication/*/deltas/*.xml"))

for snapshot in sorted(snapshots):

    time.sleep(1)
    run("rm", "-rf", "rcynic-data")
    run(rrdp_test_tool, snapshots[snapshot])
    run(rcynic, "-c", "rcynic-rrdp.conf")
    run(rcynic_text, "rcynic.xml")

    for delta in sorted(deltas):
        if delta > snapshot:
            time.sleep(1)
            run(rrdp_test_tool, deltas[delta])
            run(rcynic, "-c", "rcynic-rrdp.conf")
            run(rcynic_text, "rcynic.xml")

    if not args.exhaustive:
        break
