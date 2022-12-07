# Generated by Django 3.2 on 2022-12-07 06:30

from django.db import migrations, models
import django_extensions.db.fields
import shortuuid.main


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0004_auto_20221205_1725'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='updated_user',
            field=models.CharField(blank=True, max_length=20, verbose_name='Редактор'),
        ),
        migrations.AlterField(
            model_name='lead',
            name='passwd',
            field=django_extensions.db.fields.ShortUUIDField(blank=True, default=shortuuid.main.ShortUUID.uuid, editable=False, verbose_name='Пароль'),
        ),
    ]