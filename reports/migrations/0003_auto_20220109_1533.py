# Generated by Django 3.2.11 on 2022-01-09 10:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0002_auto_20210401_2134'),
    ]

    operations = [
        migrations.AddField(
            model_name='reports',
            name='patient_chasing_number',
            field=models.CharField(default=1, max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='reports',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='reports',
            name='pin_code',
            field=models.CharField(blank=True, max_length=6),
        ),
    ]
