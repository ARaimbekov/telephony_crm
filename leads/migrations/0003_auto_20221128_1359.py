# Generated by Django 3.2 on 2022-11-28 05:59

from django.db import migrations, models
import django_extensions.db.fields
import shortuuid.main


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0002_auto_20221101_0950'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lead',
            name='passwd',
            field=django_extensions.db.fields.ShortUUIDField(blank=True, default=shortuuid.main.ShortUUID.uuid, editable=False, verbose_name='Пароль'),
        ),
        migrations.AlterField(
            model_name='lead',
            name='update_added',
            field=models.DateTimeField(auto_now=True, verbose_name='Дата изменения'),
        ),
    ]
