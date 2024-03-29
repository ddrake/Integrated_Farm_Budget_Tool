# Generated by Django 4.2 on 2023-05-20 17:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ext', '0001_initial'),
        ('main', '0003_alter_farmcrop_frac_yield_dep_nonland_cost'),
    ]

    operations = [
        migrations.RenameField(
            model_name='farmbudgetcrop',
            old_name='assumed_basis',
            new_name='yield_variability',
        ),
        migrations.AddField(
            model_name='farmbudgetcrop',
            name='description',
            field=models.CharField(default='', max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='farmbudgetcrop',
            name='state',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='budget_crops', to='ext.state'),
        ),
    ]
