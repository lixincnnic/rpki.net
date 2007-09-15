# $Id$

"""
Start at the RPKI daemon.  This isn't real yet.  So far it's just a
framework onto which I'm bolting various parts for testing.
"""

import rpki.https, tlslite.api, rpki.config, rpki.resource_set, MySQLdb, rpki.cms

def decode(msg, cms_ta):
  return lxml.etree.fromstring(rpki.cms.decode(msg, cms_ta))

def encode(msg, cms_key, cms_certs):
  return rpki.cms.encode(lxml.etree.tostring(msg, pretty_print=True, encoding="us-ascii", xml_declaration=True), cms_key, cms_certs)

def left_right_handler(query, path):
  try:
    q_elt = decode(query, cms_ta_irbe)
    rng.assertValid(q_elt)
    saxer = rpki.left_right.sax_handler()
    lxml.sax.saxify(q_elt, saxer)
    q_msg = saxer.result
    r_msg = rpki.left_right.msg()
    for q_pdu in q_msg:
      assert isinstance(q_pdu, rpki.left_right.data_elt) and q_pdu.type == "query"

      r_pdu = q_pdu.__class__()
      r_pdu.action = q_pdu.action
      r_pdu.type = "reply"

      if q_pdu.action == "destroy":
        r_pdu.self_id = q_pdu.self_id
        setattr(r_pdu, q_pdu.sql_id_name, getattr(q_pdu, q_pdu.sql_id_name))
        q_pdu.sql_delete()
      elif q_pdu.action == "create":
        q_pdu.sql_store(db, cur)
        r_pdu.self_id = q_pdu.self_id
        setattr(r_pdu, q_pdu.sql_id_name, getattr(q_pdu, q_pdu.sql_id_name))
      else:
        rpki.left_right.self_elt.sql_fetch(db, cur, { "self_id" : q_pdu.self_id })

        # Do something useful here
        raise NotImplementedError

      r_msg.append(r_pdu)
    r_elt = r_msg.toXML()
    rng.assertValid(r_elt)
    return 200, encode(r_elt, cms_key, cms_certs)

  except Exception, data:
    return 500, "Unhandled exception %s" % data

def up_down_handler(query, path):
  raise NotImplementedError

def cronjob_handler(query, path):
  raise NotImplementedError

cfg = rpki.config.parser("re.conf")
section = "rpki"

db = MySQLdb.connect(user   = cfg.get(section, "sql-username"),
                     db     = cfg.get(section, "sql-database"),
                     passwd = cfg.get(section, "sql-password"))

cur = db.cursor()

cms_ta_irdb = cfg.get(section, "cms-ta-irdb")
cms_ta_irbe = cfg.get(section, "cms-ta-irbe")
cms_key     = cfg.get(section, "cms-key")
cms_certs   = cfg.multiget(section, "cms-cert")

https_key   = rpki.x509.RSA_Keypair(PEM_file = cfg.get(section, "https-key"))
https_certs = certChain = rpki.x509.X509_chain()

https_certs.load_from_PEM(cfg.multiget(section, "https-cert"))

rpki.https.server(privateKey=https_key, certChain=https_certs,
                  handlers=(("/left-right", left_right_handler),
                            ("/up-down",    up_down_handler),
                            ("/cronjob",    cronjob_handler)))
