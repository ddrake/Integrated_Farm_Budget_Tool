# Generated by Django 4.2.2 on 2023-07-02 17:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0031_alter_farmyear_eligible_persons_for_cap'),
    ]

    operations = [
        migrations.AddField(
            model_name='farmbudgetcrop',
            name='farm_yield_final_on',
            field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name='farmbudgetcrop',
            name='is_farm_yield_final',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='farmyear',
            name='sensitivity_data',
            field=models.JSONField(blank=True, null=True),
        ),
    ]