# Generated by Django 4.2.2 on 2023-06-30 20:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0027_remove_farmyear_report_type_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='farmbudgetcrop',
            name='budget_date',
            field=models.DateField(null=True),
        ),
    ]
