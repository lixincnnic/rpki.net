# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Alert'
        db.create_table('app_alert', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('conf', self.gf('django.db.models.fields.related.ForeignKey')(related_name='alerts', to=orm['irdb.ResourceHolderCA'])),
            ('severity', self.gf('django.db.models.fields.SmallIntegerField')(default=0)),
            ('when', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('seen', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=66)),
            ('text', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('app', ['Alert'])


    def backwards(self, orm):
        # Deleting model 'Alert'
        db.delete_table('app_alert')


    models = {
        'app.alert': {
            'Meta': {'object_name': 'Alert'},
            'conf': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'alerts'", 'to': "orm['irdb.ResourceHolderCA']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'seen': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'severity': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '66'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'when': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'app.confacl': {
            'Meta': {'unique_together': "(('user', 'conf'),)", 'object_name': 'ConfACL'},
            'conf': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['irdb.ResourceHolderCA']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'app.ghostbusterrequest': {
            'Meta': {'ordering': "('family_name', 'given_name')", 'object_name': 'GhostbusterRequest', '_ormbases': ['irdb.GhostbusterRequest']},
            'additional_name': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'box': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'country': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'email_address': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'extended': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'family_name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'full_name': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'ghostbusterrequest_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['irdb.GhostbusterRequest']", 'unique': 'True', 'primary_key': 'True'}),
            'given_name': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'honorific_prefix': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'honorific_suffix': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'organization': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'region': ('django.db.models.fields.CharField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'street': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'telephone': ('rpki.gui.app.models.TelephoneField', [], {'max_length': '40', 'null': 'True', 'blank': 'True'})
        },
        'app.resourcecert': {
            'Meta': {'object_name': 'ResourceCert'},
            'conf': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'certs'", 'to': "orm['irdb.ResourceHolderCA']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'not_after': ('django.db.models.fields.DateTimeField', [], {}),
            'not_before': ('django.db.models.fields.DateTimeField', [], {}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'certs'", 'null': 'True', 'to': "orm['irdb.Parent']"}),
            'uri': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'app.resourcerangeaddressv4': {
            'Meta': {'ordering': "('prefix_min',)", 'object_name': 'ResourceRangeAddressV4'},
            'cert': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'address_ranges'", 'to': "orm['app.ResourceCert']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'prefix_max': ('rpki.gui.models.IPv4AddressField', [], {'db_index': 'True'}),
            'prefix_min': ('rpki.gui.models.IPv4AddressField', [], {'db_index': 'True'})
        },
        'app.resourcerangeaddressv6': {
            'Meta': {'ordering': "('prefix_min',)", 'object_name': 'ResourceRangeAddressV6'},
            'cert': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'address_ranges_v6'", 'to': "orm['app.ResourceCert']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'prefix_max': ('rpki.gui.models.IPv6AddressField', [], {'db_index': 'True'}),
            'prefix_min': ('rpki.gui.models.IPv6AddressField', [], {'db_index': 'True'})
        },
        'app.resourcerangeas': {
            'Meta': {'ordering': "('min', 'max')", 'object_name': 'ResourceRangeAS'},
            'cert': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'asn_ranges'", 'to': "orm['app.ResourceCert']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'min': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        'app.timestamp': {
            'Meta': {'object_name': 'Timestamp'},
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'primary_key': 'True'}),
            'ts': ('django.db.models.fields.DateTimeField', [], {})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'irdb.ghostbusterrequest': {
            'Meta': {'object_name': 'GhostbusterRequest'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issuer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ghostbuster_requests'", 'to': "orm['irdb.ResourceHolderCA']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ghostbuster_requests'", 'null': 'True', 'to': "orm['irdb.Parent']"}),
            'vcard': ('django.db.models.fields.TextField', [], {})
        },
        'irdb.parent': {
            'Meta': {'unique_together': "(('issuer', 'handle'),)", 'object_name': 'Parent', '_ormbases': ['irdb.Turtle']},
            'certificate': ('rpki.irdb.models.CertificateField', [], {'default': 'None', 'blank': 'True'}),
            'child_handle': ('rpki.irdb.models.HandleField', [], {'max_length': '120'}),
            'handle': ('rpki.irdb.models.HandleField', [], {'max_length': '120'}),
            'issuer': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'parents'", 'to': "orm['irdb.ResourceHolderCA']"}),
            'parent_handle': ('rpki.irdb.models.HandleField', [], {'max_length': '120'}),
            'referral_authorization': ('rpki.irdb.models.SignedReferralField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'referrer': ('rpki.irdb.models.HandleField', [], {'max_length': '120', 'null': 'True', 'blank': 'True'}),
            'repository_type': ('rpki.irdb.models.EnumField', [], {}),
            'ta': ('rpki.irdb.models.CertificateField', [], {'default': 'None', 'blank': 'True'}),
            'turtle_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['irdb.Turtle']", 'unique': 'True', 'primary_key': 'True'})
        },
        'irdb.resourceholderca': {
            'Meta': {'object_name': 'ResourceHolderCA'},
            'certificate': ('rpki.irdb.models.CertificateField', [], {'default': 'None', 'blank': 'True'}),
            'handle': ('rpki.irdb.models.HandleField', [], {'unique': 'True', 'max_length': '120'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_crl_update': ('rpki.irdb.models.SundialField', [], {}),
            'latest_crl': ('rpki.irdb.models.CRLField', [], {'default': 'None', 'blank': 'True'}),
            'next_crl_number': ('django.db.models.fields.BigIntegerField', [], {'default': '1'}),
            'next_crl_update': ('rpki.irdb.models.SundialField', [], {}),
            'next_serial': ('django.db.models.fields.BigIntegerField', [], {'default': '1'}),
            'private_key': ('rpki.irdb.models.RSAKeyField', [], {'default': 'None', 'blank': 'True'})
        },
        'irdb.turtle': {
            'Meta': {'object_name': 'Turtle'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'service_uri': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['app']