# Generated by Django 3.0.8 on 2020-08-07 12:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('musicboard', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='musicpost',
            name='isAdded',
            field=models.BooleanField(default=False),
        ),
    ]
