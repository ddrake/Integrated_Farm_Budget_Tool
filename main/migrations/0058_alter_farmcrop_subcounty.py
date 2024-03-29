# Generated by Django 5.0.1 on 2024-01-23 21:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0057_rename_ta_use_farmcrop_ta_rename_ye_use_farmcrop_ye_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='farmcrop',
            name='subcounty',
            field=models.CharField(blank=True, choices=[('AAA', 'AAA'), ('BBB', 'BBB'), ('CCC', 'CCC'), ('DDD', 'DDD'), ('EEE', 'EEE'), ('FFF', 'FFF'), ('GGG', 'GGG'), ('HHH', 'HHH'), ('III', 'III'), ('JJJ', 'JJJ'), ('LLL', 'LLL'), ('MMM', 'MMM'), ('NNN', 'NNN'), ('PPP', 'PPP'), ('QQQ', 'QQQ'), ('RRR', 'RRR'), ('URA', 'URA'), ('SSS', 'SSS'), ('TTT', 'TTT'), ('VVV', 'VVV')], default='', help_text='Primary risk class (subcounty ID) provided by crop insurer', max_length=8, verbose_name='risk class'),
        ),
    ]
