# Generated by Django 4.2.7 on 2023-11-28 18:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0056_rename_ta_aph_yield_farmcrop_appr_yield'),
    ]

    operations = [
        migrations.RenameField(
            model_name='farmcrop',
            old_name='ta_use',
            new_name='ta',
        ),
        migrations.RenameField(
            model_name='farmcrop',
            old_name='ye_use',
            new_name='ye',
        ),
        migrations.AddField(
            model_name='farmcrop',
            name='ql',
            field=models.BooleanField(default=False, help_text='Apply quality loss option?', verbose_name='use QL?'),
        ),
        migrations.AddField(
            model_name='farmcrop',
            name='ya',
            field=models.BooleanField(default=False, help_text='Apply yield averaging option?', verbose_name='use YA?'),
        ),
        migrations.AddField(
            model_name='farmcrop',
            name='yc',
            field=models.BooleanField(default=False, help_text='Apply yield cup option?', verbose_name='use YC?'),
        ),
    ]
