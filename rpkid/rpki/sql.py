# $Id$

# Copyright (C) 2007--2008  American Registry for Internet Numbers ("ARIN")
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND ARIN DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS.  IN NO EVENT SHALL ARIN BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
# OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

import MySQLdb, time
import rpki.x509, rpki.resource_set, rpki.sundial

def connect(cfg):
  """Connect to a MySQL database using connection parameters from an
     rpki.config.parser object.
  """
  return MySQLdb.connect(user   = cfg.get("sql-username"),
                         db     = cfg.get("sql-database"),
                         passwd = cfg.get("sql-password"))

class template(object):
  """SQL template generator."""
  def __init__(self, table_name, index_column, *data_columns):
    """Build a SQL template."""
    type_map     = dict((x[0],x[1]) for x in data_columns if isinstance(x, tuple))
    data_columns = tuple(isinstance(x, tuple) and x[0] or x for x in data_columns)
    columns      = (index_column,) + data_columns
    self.table   = table_name
    self.index   = index_column
    self.columns = columns
    self.map     = type_map
    self.select  = "SELECT %s FROM %s" % (", ".join(columns), table_name)
    self.insert  = "INSERT %s (%s) VALUES (%s)" % (table_name, ", ".join(data_columns),
                                                   ", ".join("%(" + s + ")s" for s in data_columns))
    self.update  = "UPDATE %s SET %s WHERE %s = %%(%s)s" % \
                   (table_name, ", ".join(s + " = %(" + s + ")s" for s in data_columns),
                    index_column, index_column)
    self.delete  = "DELETE FROM %s WHERE %s = %%s" % (table_name, index_column)

## @var sql_cache
# Cache of objects pulled from SQL.

sql_cache = {}

## @var sql_dirty
# Set of objects that need to be written back to SQL.

sql_dirty = set()

def sql_cache_clear():
  """Clear the object cache."""
  sql_cache.clear()

def sql_assert_pristine():
  """Assert that there are no dirty objects in the cache."""
  assert not sql_dirty, "Dirty objects in SQL cache: %s" % sql_dirty

def sql_sweep(gctx):
  """Write any dirty objects out to SQL."""
  for s in sql_dirty.copy():
    rpki.log.debug("Sweeping %s" % repr(s))
    s.sql_store(gctx)
  sql_assert_pristine()

class sql_persistant(object):
  """Mixin for persistant class that needs to be stored in SQL.
  """

  ## @var sql_in_db
  # Whether this object is already in SQL or not.
  sql_in_db = False

  @classmethod
  def sql_fetch(cls, gctx, id):
    """Fetch one object from SQL, based on its primary key.  Since in
    this one case we know that the primary index is also the cache
    key, we check for a cache hit directly in the hope of bypassing the
    SQL lookup entirely.
    """
    key = (cls, id)
    if key in sql_cache:
      return sql_cache[key]
    else:
      return cls.sql_fetch_where1(gctx, "%s = %s", (cls.sql_template.index, id))

  @classmethod
  def sql_fetch_where1(cls, gctx, where, args = None):
    """Fetch one object from SQL, based on an arbitrary SQL WHERE expression."""
    results = cls.sql_fetch_where(gctx, where, args)
    if len(results) == 0:
      return None
    elif len(results) == 1:
      return results[0]
    else:
      raise rpki.exceptions.DBConsistancyError, \
            "Database contained multiple matches for %s where %s" % \
            (cls.__name__, where % tuple(repr(a) for a in args))

  @classmethod
  def sql_fetch_all(cls, gctx):
    """Fetch all objects of this type from SQL."""
    return cls.sql_fetch_where(gctx, None)

  @classmethod
  def sql_fetch_where(cls, gctx, where, args = None):
    """Fetch objects of this type matching an arbitrary SQL WHERE expression."""
    if where is None:
      gctx.cur.execute(cls.sql_template.select)
    else:
      gctx.cur.execute(cls.sql_template.select + " WHERE " + where, args)
    results = []
    for row in gctx.cur.fetchall():
      key = (cls, row[0])
      if key in sql_cache:
        results.append(sql_cache[key])
      else:
        results.append(cls.sql_init(gctx, row, key))
    return results

  @classmethod
  def sql_init(cls, gctx, row, key):
    """Initialize one Python object from the result of a SQL query."""
    self = cls()
    self.sql_decode(dict(zip(cls.sql_template.columns, row)))
    sql_cache[key] = self
    self.sql_in_db = True
    self.sql_fetch_hook(gctx)
    return self

  def sql_mark_dirty(self):
    """Mark this object as needing to be written back to SQL."""
    sql_dirty.add(self)

  def sql_mark_clean(self):
    """Mark this object as not needing to be written back to SQL."""
    sql_dirty.discard(self)

  def sql_is_dirty(self):
    """Query whether this object needs to be written back to SQL."""
    return self in sql_dirty

  def sql_store(self, gctx):
    """Store this object to SQL."""
    if not self.sql_in_db:
      gctx.cur.execute(self.sql_template.insert, self.sql_encode())
      setattr(self, self.sql_template.index, gctx.cur.lastrowid)
      sql_cache[(self.__class__, gctx.cur.lastrowid)] = self
      self.sql_insert_hook(gctx)
    else:
      gctx.cur.execute(self.sql_template.update, self.sql_encode())
      self.sql_update_hook(gctx)
    key = (self.__class__, getattr(self, self.sql_template.index))
    assert key in sql_cache and sql_cache[key] == self
    self.sql_mark_clean()
    self.sql_in_db = True

  def sql_delete(self, gctx):
    """Delete this object from SQL."""
    if self.sql_in_db:
      id = getattr(self, self.sql_template.index)
      gctx.cur.execute(self.sql_template.delete, id)
      self.sql_delete_hook(gctx)
      key = (self.__class__, id)
      if sql_cache.get(key) == self:
        del sql_cache[key]
      self.sql_in_db = False
      self.sql_mark_clean()

  def sql_encode(self):
    """Convert object attributes into a dict for use with canned SQL
    queries.  This is a default version that assumes a one-to-one
    mapping between column names in SQL and attribute names in Python.
    If you need something fancier, override this.
    """
    d = dict((a, getattr(self, a, None)) for a in self.sql_template.columns)
    for i in self.sql_template.map:
      if d.get(i) is not None:
        d[i] = self.sql_template.map[i].to_sql(d[i])
    return d

  def sql_decode(self, vals):
    """Initialize an object with values returned by self.sql_fetch().
    This is a default version that assumes a one-to-one mapping
    between column names in SQL and attribute names in Python.  If you
    need something fancier, override this.
    """
    for a in self.sql_template.columns:
      if vals.get(a) is not None and a in self.sql_template.map:
        setattr(self, a, self.sql_template.map[a].from_sql(vals[a]))
      else:
        setattr(self, a, vals[a])

  def sql_fetch_hook(self, gctx):
    """Customization hook."""
    pass

  def sql_insert_hook(self, gctx):
    """Customization hook."""
    pass
  
  def sql_update_hook(self, gctx):
    """Customization hook."""
    self.sql_delete_hook(gctx)
    self.sql_insert_hook(gctx)

  def sql_delete_hook(self, gctx):
    """Customization hook."""
    pass

# Some persistant objects are defined in rpki.left_right, since
# they're also left-right PDUs.  The rest are defined below, for now.

class ca_obj(sql_persistant):
  """Internal CA object."""

  sql_template = template(
    "ca", "ca_id", "last_crl_sn",
    ("next_crl_update", rpki.sundial.datetime),
    "last_issued_sn", "last_manifest_sn",
    ("next_manifest_update", rpki.sundial.datetime),
    "sia_uri", "parent_id", "parent_resource_class")

  last_crl_sn = 0
  last_issued_sn = 0
  last_manifest_sn = 0

  def parent(self, gctx):
    """Fetch parent object to which this CA object links."""
    return rpki.left_right.parent_elt.sql_fetch(gctx, self.parent_id)

  def ca_details(self, gctx):
    """Fetch all ca_detail objects that link to this CA object."""
    return ca_detail_obj.sql_fetch_where(gctx, "ca_id = %s", (self.ca_id,))

  def fetch_pending(self, gctx):
    """Fetch the pending ca_details for this CA, if any."""
    return ca_detail_obj.sql_fetch_where(gctx, "ca_id = %s AND state = 'pending'", (self.ca_id,))

  def fetch_active(self, gctx):
    """Fetch the active ca_detail for this CA, if any."""
    return ca_detail_obj.sql_fetch_where1(gctx, "ca_id = %s AND state = 'active'", (self.ca_id,))

  def fetch_deprecated(self, gctx):
    """Fetch deprecated ca_details for this CA, if any."""
    return ca_detail_obj.sql_fetch_where(gctx, "ca_id = %s AND state = 'deprecated'", (self.ca_id,))

  def fetch_revoked(self, gctx):
    """Fetch revoked ca_details for this CA, if any."""
    return ca_detail_obj.sql_fetch_where(gctx, "ca_id = %s AND state = 'revoked'", (self.ca_id,))

  def construct_sia_uri(self, gctx, parent, rc):
    """Construct the sia_uri value for this CA given configured
    information and the parent's up-down protocol list_response PDU.
    """

    repository = parent.repository(gctx)
    sia_uri = rc.suggested_sia_head and rc.suggested_sia_head.rsync()
    if not sia_uri or not sia_uri.startswith(parent.sia_base):
      sia_uri = parent.sia_base
    elif not sia_uri.endswith("/"):
      raise rpki.exceptions.BadURISyntax, "SIA URI must end with a slash: %s" % sia_uri
    return sia_uri + str(self.ca_id) + "/"

  def check_for_updates(self, gctx, parent, rc):
    """Parent has signaled continued existance of a resource class we
    already knew about, so we need to check for an updated
    certificate, changes in resource coverage, revocation and reissue
    with the same key, etc.
    """

    sia_uri = self.construct_sia_uri(gctx, parent, rc)
    sia_uri_changed = self.sia_uri != sia_uri
    if sia_uri_changed:
      self.sia_uri = sia_uri
      self.sql_mark_dirty()

    rc_resources = rc.to_resource_bag()
    cert_map = dict((c.cert.get_SKI(), c) for c in rc.certs)

    for ca_detail in ca_detail_obj.sql_fetch_where(gctx, "ca_id = %s AND latest_ca_cert IS NOT NULL AND state != 'revoked'", (self.ca_id,)):
      ski = ca_detail.latest_ca_cert.get_SKI()
      if ca_detail.state in ("pending", "active"):
        current_resources = ca_detail.latest_ca_cert.get_3779resources()
        if sia_uri_changed or \
             ca_detail.latest_ca_cert != cert_map[ski].cert or \
             current_resources.undersized(rc_resources) or \
             current_resources.oversized(rc_resources):
          ca_detail.update(
            gctx             = gctx,
            parent           = parent,
            ca               = self,
            rc               = rc,
            sia_uri_changed  = sia_uri_changed,
            old_resources    = current_resources)
      del cert_map[ski]
    assert not cert_map, "Certificates in list_response missing from our database, SKIs %s" % ", ".join(c.cert.hSKI() for c in cert_map.values())

  @classmethod
  def create(cls, gctx, parent, rc):
    """Parent has signaled existance of a new resource class, so we
    need to create and set up a corresponding CA object.
    """

    self = cls()
    self.parent_id = parent.parent_id
    self.parent_resource_class = rc.class_name
    self.sql_store(gctx)
    self.sia_uri = self.construct_sia_uri(gctx, parent, rc)
    ca_detail = ca_detail_obj.create(gctx, self)

    # This will need a callback when we go event-driven
    issue_response = rpki.up_down.issue_pdu.query(gctx, parent, self, ca_detail)

    ca_detail.activate(
      gctx = gctx,
      ca   = self,
      cert = issue_response.payload.classes[0].certs[0].cert,
      uri  = issue_response.payload.classes[0].certs[0].cert_url)

  def delete(self, gctx, parent):
    """The list of current resource classes received from parent does
    not include the class corresponding to this CA, so we need to
    delete it (and its little dog too...).

    All certs published by this CA are now invalid, so need to
    withdraw them, the CRL, and the manifest from the repository,
    delete all child_cert and ca_detail records associated with this
    CA, then finally delete this CA itself.
    """

    repository = parent.repository(gctx)
    for ca_detail in self.ca_details(gctx):
      ca_detail.delete(gctx, ca, repository)
    self.sql_delete(gctx)

  def next_serial_number(self):
    """Allocate a certificate serial number."""
    self.last_issued_sn += 1
    self.sql_mark_dirty()
    return self.last_issued_sn

  def next_manifest_number(self):
    """Allocate a manifest serial number."""
    self.last_manifest_sn += 1
    self.sql_mark_dirty()
    return self.last_manifest_sn

  def next_crl_number(self):
    """Allocate a CRL serial number."""
    self.last_crl_sn += 1
    self.sql_mark_dirty()
    return self.last_crl_sn

  def rekey(self, gctx):
    """Initiate a rekey operation for this ca.

    Tasks:

    - Generate a new keypair.

    - Request cert from parent using new keypair.

    - Mark result as our active ca_detail.

    - Reissue all child certs issued by this ca using the new ca_detail.
    """

    rpki.log.trace()

    parent = self.parent(gctx)
    old_detail = self.fetch_active(gctx)
    new_detail = ca_detail_obj.create(gctx, self)

    # This will need a callback when we go event-driven
    issue_response = rpki.up_down.issue_pdu.query(gctx, parent, self, new_detail)

    new_detail.activate(
      gctx        = gctx,
      ca          = self,
      cert        = issue_response.payload.classes[0].certs[0].cert,
      uri         = issue_response.payload.classes[0].certs[0].cert_url,
      predecessor = old_detail)

  def revoke(self, gctx):
    """Revoke deprecated ca_detail objects associated with this ca."""

    rpki.log.trace()

    for ca_detail in self.fetch_deprecated(gctx):
      ca_detail.revoke(gctx)

class ca_detail_obj(sql_persistant):
  """Internal CA detail object."""

  sql_template = template(
    "ca_detail",
    "ca_detail_id",
    ("private_key_id",          rpki.x509.RSA),
    ("public_key",              rpki.x509.RSApublic),
    ("latest_ca_cert",          rpki.x509.X509),
    ("manifest_private_key_id", rpki.x509.RSA),
    ("manifest_public_key",     rpki.x509.RSApublic),
    ("latest_manifest_cert",    rpki.x509.X509),
    ("latest_manifest",         rpki.x509.SignedManifest),
    ("latest_crl",              rpki.x509.CRL),
    "state",
    "ca_cert_uri",
    "ca_id")
  
  def sql_decode(self, vals):
    """Extra assertions for SQL decode of a ca_detail_obj."""
    sql_persistant.sql_decode(self, vals)
    assert (self.public_key is None and self.private_key_id is None) or \
           self.public_key.get_DER() == self.private_key_id.get_public_DER()
    assert (self.manifest_public_key is None and self.manifest_private_key_id is None) or \
           self.manifest_public_key.get_DER() == self.manifest_private_key_id.get_public_DER()

  def ca(self, gctx):
    """Fetch CA object to which this ca_detail links."""
    return ca_obj.sql_fetch(gctx, self.ca_id)

  def child_certs(self, gctx, child = None, ski = None, revoked = False, unique = False):
    """Fetch all child_cert objects that link to this ca_detail."""
    return rpki.sql.child_cert_obj.fetch(gctx, child, self, ski, revoked, unique)

  def route_origins(self, gctx):
    """Fetch all route_origin objects that link to this ca_detail."""
    return rpki.left_right.route_origin_elt.sql_fetch_where(gctx, "ca_detail_id = %s", (self.ca_detail_id,))

  def crl_uri(self, ca):
    """Return publication URI for this ca_detail's CRL."""
    return ca.sia_uri + self.public_key.gSKI() + ".crl"

  def manifest_uri(self, ca):
    """Return publication URI for this ca_detail's manifest."""
    return ca.sia_uri + self.public_key.gSKI() + ".mnf"

  def activate(self, gctx, ca, cert, uri, predecessor = None):
    """Activate this ca_detail."""

    self.latest_ca_cert = cert
    self.ca_cert_uri = uri.rsync()
    self.generate_manifest_cert(ca)
    self.generate_crl(gctx)
    self.generate_manifest(gctx)
    self.state = "active"
    self.sql_mark_dirty()

    if predecessor is not None:
      predecessor.state = "deprecated"
      predecessor.sql_mark_dirty()
      for child_cert in predecessor.child_certs(gctx):
        child_cert.reissue(gctx, self)

  def delete(self, gctx, ca, repository):
    """Delete this ca_detail and all of its associated child_cert objects."""

    for child_cert in self.child_certs(gctx):
      repository.withdraw(gctx, child_cert.cert, child_cert.uri(ca))
      child_cert.sql_delete(gctx)
    for child_cert in self.child_certs(gctx, revoked = True):
      child_cert.sql_delete(gctx)
    repository.withdraw(gctx, self.latest_manifest, self.manifest_uri(ca))
    repository.withdraw(gctx, self.latest_crl, self.crl_uri())
    self.sql_delete(gctx)

  def revoke(self, gctx):
    """Request revocation of all certificates whose SKI matches the key for this ca_detail.

    Tasks:

    - Request revocation of old keypair by parent.

    - Revoke all child certs issued by the old keypair.

    - Generate a final CRL, signed with the old keypair, listing all
      the revoked certs, with a next CRL time after the last cert or
      CRL signed by the old keypair will have expired.

    - Destroy old keypair (and manifest keypair).

    - Leave final CRL in place until its next CRL time has passed.
    """

    # This will need a callback when we go event-driven
    r_msg = rpki.up_down.revoke_pdu.query(gctx, self)

    if r_msg.payload.ski != self.latest_ca_cert.gSKI():
      raise rpki.exceptions.SKIMismatch

    ca = self.ca(gctx)
    parent = ca.parent(gctx)
    crl_interval = rpki.sundial.timedelta(seconds = parent.self(gctx).crl_interval)

    nextUpdate = rpki.sundial.datetime.utcnow()

    if self.latest_manifest is not None:
      nextUpdate = nextUpdate.later(self.latest_manifest.getNextUpdate())

    if self.latest_crl is not None:
      nextUpdate = nextUpdate.later(self.latest_crl.getNextUpdate())

    for child_cert in self.child_certs(gctx):
      nextUpdate = nextUpdate.later(child_cert.cert.getNotAfter())
      child_cert.revoke(gctx)

    nextUpdate += crl_interval

    self.generate_crl(gctx, nextUpdate)
    self.generate_manifest(gctx, nextUpdate)

    self.private_key_id = None
    self.manifest_private_key_id = None
    self.manifest_public_key = None
    self.latest_manifest_cert = None
    self.state = "revoked"
    self.sql_mark_dirty()

  def update(self, gctx, parent, ca, rc, sia_uri_changed, old_resources):
    """Need to get a new certificate for this ca_detail and perhaps
    frob children of this ca_detail.
    """

    # This will need a callback when we go event-driven
    issue_response = rpki.up_down.issue_pdu.query(gctx, parent, ca, self)

    self.latest_ca_cert = issue_response.payload.classes[0].certs[0].cert
    new_resources = self.latest_ca_cert.get_3779resources()

    if sia_uri_changed or old_resources.oversized(new_resources):
      for child_cert in self.child_certs(gctx):
        child_resources = child_cert.cert.get_3779resources()
        if sia_uri_changed or child_resources.oversized(new_resources):
          child_cert.reissue(
            gctx      = gctx,
            ca_detail = self,
            resources = child_resources.intersection(new_resources))

  @classmethod
  def create(cls, gctx, ca):
    """Create a new ca_detail object for a specified CA."""
    self = cls()
    self.ca_id = ca.ca_id
    self.state = "pending"

    self.private_key_id = rpki.x509.RSA()
    self.private_key_id.generate()
    self.public_key = self.private_key_id.get_RSApublic()

    self.manifest_private_key_id = rpki.x509.RSA()
    self.manifest_private_key_id.generate()
    self.manifest_public_key = self.manifest_private_key_id.get_RSApublic()

    self.sql_store(gctx)
    return self

  def issue_ee(self, ca, resources, sia = None):
    """Issue a new EE certificate."""

    return self.latest_ca_cert.issue(
      keypair     = self.private_key_id,
      subject_key = self.manifest_public_key,
      serial      = ca.next_serial_number(),
      sia         = sia,
      aia         = self.ca_cert_uri,
      crldp       = self.crl_uri(ca),
      resources   = resources,
      notAfter    = self.latest_ca_cert.getNotAfter(),
      is_ca       = False)


  def generate_manifest_cert(self, ca):
    """Generate a new manifest certificate for this ca_detail."""

    resources = rpki.resource_set.resource_bag(
      as = rpki.resource_set.resource_set_as("<inherit>"),
      v4 = rpki.resource_set.resource_set_ipv4("<inherit>"),
      v6 = rpki.resource_set.resource_set_ipv6("<inherit>"))

    self.latest_manifest_cert = self.issue_ee(ca, resources)

  def issue(self, gctx, ca, child, subject_key, sia, resources, child_cert = None):
    """Issue a new certificate to a child.  Optional child_cert
    argument specifies an existing child_cert object to update in
    place; if not specified, we create a new one.  Returns the
    child_cert object containing the newly issued cert.
    """

    assert child_cert is None or (child_cert.child_id == child.child_id and
                                  child_cert.ca_detail_id == self.ca_detail_id)

    cert = self.latest_ca_cert.issue(
      keypair     = self.private_key_id,
      subject_key = subject_key,
      serial      = ca.next_serial_number(),
      aia         = self.ca_cert_uri,
      crldp       = self.crl_uri(ca),
      sia         = sia,
      resources   = resources,
      notAfter    = resources.valid_until)

    if child_cert is None:
      child_cert = rpki.sql.child_cert_obj(
        child_id     = child.child_id,
        ca_detail_id = self.ca_detail_id,
        cert         = cert)
      rpki.log.debug("Created new child_cert %s" % repr(child_cert))
    else:
      child_cert.cert = cert
      rpki.log.debug("Reusing existing child_cert %s" % repr(child_cert))

    child_cert.ski = cert.get_SKI()

    child_cert.sql_store(gctx)

    ca.parent(gctx).repository(gctx).publish(gctx, child_cert.cert, child_cert.uri(ca))

    self.generate_manifest(gctx)
    
    return child_cert

  def generate_crl(self, gctx, nextUpdate = None):
    """Generate a new CRL for this ca_detail.  At the moment this is
    unconditional, that is, it is up to the caller to decide whether a
    new CRL is needed.
    """

    ca = self.ca(gctx)
    parent = ca.parent(gctx)
    repository = parent.repository(gctx)
    crl_interval = rpki.sundial.timedelta(seconds = parent.self(gctx).crl_interval)
    now = rpki.sundial.datetime.utcnow()

    if nextUpdate is None:
      nextUpdate = now + crl_interval

    certlist = []
    for child_cert in self.child_certs(gctx, revoked = True):
      if now > child_cert.cert.getNotAfter() + crl_interval:
        child_cert.sql_delete()
      else:
        certlist.append((child_cert.cert.getSerial(), child_cert.revoked.toASN1tuple(), ()))
    certlist.sort()

    self.latest_crl = rpki.x509.CRL.generate(
      keypair             = self.private_key_id,
      issuer              = self.latest_ca_cert,
      serial              = ca.next_crl_number(),
      thisUpdate          = now,
      nextUpdate          = nextUpdate,
      revokedCertificates = certlist)

    repository.publish(gctx, self.latest_crl, self.crl_uri(ca))

  def generate_manifest(self, gctx, nextUpdate = None):
    """Generate a new manifest for this ca_detail."""

    ca = self.ca(gctx)
    parent = ca.parent(gctx)
    repository = parent.repository(gctx)
    crl_interval = rpki.sundial.timedelta(seconds = parent.self(gctx).crl_interval)
    now = rpki.sundial.datetime.utcnow()

    if nextUpdate is None:
      nextUpdate = now + crl_interval

    certs = [(c.uri_tail(), c.cert) for c in self.child_certs(gctx)]
    roas = [(r.uri_tail(), r.roa) for r in self.route_origins(gctx) if r is not None]

    m = rpki.x509.SignedManifest()
    m.build(
      serial         = ca.next_manifest_number(),
      thisUpdate     = now,
      nextUpdate     = nextUpdate,
      names_and_objs = certs + roas,
      keypair        = self.manifest_private_key_id,
      certs          = rpki.x509.X509_chain(self.latest_manifest_cert))
    self.latest_manifest = m

    repository.publish(gctx, self.latest_manifest, self.manifest_uri(ca))

class child_cert_obj(sql_persistant):
  """Certificate that has been issued to a child."""

  sql_template = template("child_cert", "child_cert_id", ("cert", rpki.x509.X509), "child_id", "ca_detail_id", "ski", ("revoked", rpki.sundial.datetime))

  def __init__(self, child_id = None, ca_detail_id = None, cert = None):
    """Initialize a child_cert_obj."""
    self.child_id = child_id
    self.ca_detail_id = ca_detail_id
    self.cert = cert
    self.revoked = None
    if child_id or ca_detail_id or cert:
      self.sql_mark_dirty()

  def child(self, gctx):
    """Fetch child object to which this child_cert object links."""
    return rpki.left_right.child_elt.sql_fetch(gctx, self.child_id)

  def ca_detail(self, gctx):
    """Fetch ca_detail object to which this child_cert object links."""
    return ca_detail_obj.sql_fetch(gctx, self.ca_detail_id)

  def uri_tail(self):
    """Return the tail (filename) portion of the URI for this child_cert."""
    return self.cert.gSKI() + ".cer"

  def uri(self, ca):
    """Return the publication URI for this child_cert."""
    return ca.sia_uri + self.uri_tail()

  def revoke(self, gctx):
    """Mark a child cert as revoked."""
    if self.revoked is None:
      rpki.log.debug("Revoking %s" % repr(self))
      self.revoked = rpki.sundial.datetime.utcnow()
      ca = self.ca_detail(gctx).ca(gctx)
      repository = ca.parent(gctx).repository(gctx)
      repository.withdraw(gctx, self.cert, self.uri(ca))
      self.sql_mark_dirty()

  def reissue(self, gctx, ca_detail, resources = None, sia = None):
    """Reissue an existing cert, reusing the public key.  If the cert
    we would generate is identical to the one we already have, we just
    return the one we already have.  If we have to revoke the old
    certificate when generating the new one, we have to generate a new
    child_cert_obj, so calling code that needs the updated
    child_cert_obj must use the return value from this method.
    """

    ca = ca_detail.ca(gctx)
    child = self.child(gctx)

    old_resources = self.cert.get_3779resources()
    old_sia       = self.cert.get_SIA()
    old_ca_detail = self.ca_detail(gctx)

    if resources is None:
      resources = old_resources

    if sia is None:
      sia = old_sia

    assert resources.valid_until is not None and old_resources.valid_until is not None

    if resources == old_resources and sia == old_sia and ca_detail == old_ca_detail:
      return self

    must_revoke = old_resources.oversized(resources) or old_resources.valid_until > resources.valid_until
    new_issuer  = ca_detail != old_ca_detail

    if resources.valid_until != old_resources.valid_until:
      rpki.log.debug("Validity changed: %s %s" % ( old_resources.valid_until, resources.valid_until))

    if must_revoke or new_issuer:
      child_cert = None
    else:
      child_cert = self

    child_cert = ca_detail.issue(
      gctx        = gctx,
      ca          = ca,
      child       = child,
      subject_key = self.cert.getPublicKey(),
      sia         = sia,
      resources   = resources,
      child_cert  = child_cert)

    if must_revoke:
      for cert in child.child_certs(gctx = gctx, ca_detail = ca_detail, ski = self.ski):
        if cert is not child_cert:
          cert.revoke(gctx)

    return child_cert

  @classmethod
  def fetch(cls, gctx, child = None, ca_detail = None, ski = None, revoked = False, unique = False):
    """Fetch all child_cert objects matching a particular set of
    parameters.  This is a wrapper to consolidate various queries that
    would otherwise be inline SQL WHERE expressions.  In most cases
    code calls this indirectly, through methods in other classes.
    """

    args = []
    where = "revoked IS"
    if revoked:
      where += " NOT"
    where += " NULL"
    if child:
      where += " AND child_id = %s"
      args.append(child.child_id)
    if ca_detail:
      where += " AND ca_detail_id = %s"
      args.append(ca_detail.ca_detail_id)
    if ski:
      where += " AND ski = %s"
      args.append(ski)
    if unique:
      return cls.sql_fetch_where1(gctx, where, args)
    else:
      return cls.sql_fetch_where(gctx, where, args)
