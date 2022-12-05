# Generated by Django 3.2 on 2022-12-05 09:25

from django.db import migrations, models
import django_extensions.db.fields
import shortuuid.main


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0003_auto_20221128_1359'),
    ]

    operations = [
        migrations.AlterField(
            model_name='atc',
            name='ip_address',
            field=models.CharField(max_length=30, verbose_name='IP адрес'),
        ),
        migrations.AlterField(
            model_name='lead',
            name='passwd',
            field=django_extensions.db.fields.ShortUUIDField(blank=True, default=shortuuid.main.ShortUUID.uuid, editable=False, verbose_name='Пароль'),
        ),
    ]
