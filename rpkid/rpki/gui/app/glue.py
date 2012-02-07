# Copyright (C) 2010, 2011  SPARTA, Inc. dba Cobham Analytic Solutions
# Copyright (C) 2012  SPARTA, Inc. a Parsons Company
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND SPARTA DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS.  IN NO EVENT SHALL SPARTA BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
# OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

"""
This file contains code that interfaces between the django views implementing
the portal gui and the rpki.* modules.

"""

from __future__ import with_statement

__version__ = '$Id$'

from datetime import datetime

from rpki.resource_set import (resource_set_as, resource_set_ipv4,
                               resource_set_ipv6, resource_range_ipv4,
                               resource_range_ipv6)
from rpki.left_right import list_received_resources_elt
from rpki.irdb.zookeeper import Zookeeper
from rpki.gui.app import models, settings


def ghostbuster_to_vcard(gbr):
    """Convert a GhostbusterRequest object into a vCard object."""
    import vobject

    vcard = vobject.vCard()
    vcard.add('N').value = vobject.vcard.Name(family=gbr.family_name,
                                              given=gbr.given_name)

    adr_fields = ['box', 'extended', 'street', 'city', 'region', 'code',
                  'country']
    adr_dict = dict((f, getattr(gbr, f, '')) for f in adr_fields)
    if any(adr_dict.itervalues()):
        vcard.add('ADR').value = vobject.vcard.Address(**adr_dict)

    # mapping from vCard type to Ghostbuster model field
    # the ORG type is a sequence of organization unit names, so
    # transform the org name into a tuple before stuffing into the
    # vCard object
    attrs = [('FN',    'full_name',      None),
             ('TEL',   'telephone',      None),
             ('ORG',   'organization',   lambda x: (x,)),
             ('EMAIL', 'email_address',  None)]
    for vtype, field, transform in attrs:
        v = getattr(gbr, field)
        if v:
            vcard.add(vtype).value = transform(v) if transform else v
    return vcard.serialize()


def list_received_resources(log, conf):
    """
    Query rpkid for this resource handle's received resources.

    The semantics are to clear the entire table and populate with the list of
    certs received.  Other models should not reference the table directly with
    foreign keys.

    """

    z = Zookeeper(handle=conf.handle)
    pdus = z.call_rpkid(list_received_resources_elt.make_pdu(self_handle=conf.handle))

    models.ResourceCert.objects.filter(parent__issuer=conf).delete()

    for pdu in pdus:
        if isinstance(pdu, list_received_resources_elt):
            parent = models.Parent.objects.get(issuer=conf,
                                               handle=pdu.parent_handle)

            not_before = datetime.strptime(pdu.notBefore, "%Y-%m-%dT%H:%M:%SZ")
            not_after = datetime.strptime(pdu.notAfter, "%Y-%m-%dT%H:%M:%SZ")

            cert = models.ResourceCert.objects.create(parent=parent,
                    not_before=not_before, not_after=not_after,
                    uri=pdu.uri)

            for asn in resource_set_as(pdu.asn):
                cert.asn_ranges.create(min=asn.min, max=asn.max)

            for rng in resource_set_ipv4(pdu.ipv4):
                print >>log, 'adding v4 address range: %s' % rng
                cert.address_ranges.create(prefix_min=rng.min,
                                           prefix_max=rng.max)

            for rng in resource_set_ipv6(pdu.ipv6):
                cert.address_ranges_v6.create(prefix_min=rng.min,
                                              prefix_max=rng.max)
        else:
            print >>log, "error: unexpected pdu from rpkid type=%s" % type(pdu)


def config_from_template(dest, a):
    """
    Create a new rpki.conf file from a generic template.  Go line by line
    through the template and substitute directives from the dictionary 'a'.

    """
    with open(dest, 'w') as f:
        for r in open(settings.RPKI_CONF_TEMPLATE):
            words = r.split()
            if words:
                word = words[0].strip()
                if word in a:
                    print >>f, "%s\t\t\t\t= %s\n" % (word, a[word])
                else:
                    print >>f, r,
            else:
                print >>f, r,

def str_to_resource_range(prefix):
    try:
        r = resource_range_ipv4.parse_str(prefix)
    except BadIPResource:
        r = resource_range_ipv6.parse_str(prefix)
    return r
