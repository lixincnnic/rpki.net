# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rpkidb', '0004_turtle_cleanup'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ca',
            name='parent',
            field=models.ForeignKey(related_name='cas', to='rpkidb.Turtle'),
        ),
        migrations.AlterField(
            model_name='turtle',
            name='repository',
            field=models.ForeignKey(related_name='turtles', to='rpkidb.Repository'),
        ),
        migrations.AlterField(
            model_name='turtle',
            name='tenant',
            field=models.ForeignKey(related_name='turtles', to='rpkidb.Tenant'),
        ),
    ]