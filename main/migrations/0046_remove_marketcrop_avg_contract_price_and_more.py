# Generated by Django 4.2.5 on 2023-09-20 19:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0045_farmyear_sensitivity_text'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='marketcrop',
            name='avg_contract_price',
        ),
        migrations.RemoveField(
            model_name='marketcrop',
            name='avg_locked_basis',
        ),
        migrations.RemoveField(
            model_name='marketcrop',
            name='basis_bu_locked',
        ),
        migrations.RemoveField(
            model_name='marketcrop',
            name='contracted_bu',
        ),
    ]