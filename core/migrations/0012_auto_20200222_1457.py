# Generated by Django 2.1.7 on 2020-02-22 06:57

from django.db import migrations
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_auto_20200222_1454'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='country',
            field=django_countries.fields.CountryField(default='MY', max_length=2),
        ),
    ]
