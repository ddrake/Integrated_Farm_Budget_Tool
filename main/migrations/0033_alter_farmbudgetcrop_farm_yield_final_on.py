# Generated by Django 4.2.2 on 2023-07-02 18:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0032_farmbudgetcrop_farm_yield_final_on_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='farmbudgetcrop',
            name='farm_yield_final_on',
            field=models.DateField(help_text='Adjust the farm yield and check this box once farm yield is known', null=True, verbose_name='farm yield final?'),
        ),
    ]
