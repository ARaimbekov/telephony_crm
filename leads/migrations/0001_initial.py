# Generated by Django 4.1.2 on 2022-10-26 08:23

from django.conf import settings
import django.contrib.auth.models
import django.contrib.auth.validators
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_extensions.db.fields
import re
import shortuuid.main


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('is_organisor', models.BooleanField(default=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
                'abstract': False,
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Apparats',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='Модель')),
            ],
        ),
        migrations.CreateModel(
            name='Atc',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, unique=True, verbose_name='Наименование')),
                ('ip_address', models.CharField(max_length=30, unique=True, verbose_name='IP адрес')),
            ],
        ),
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='Компании')),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
        ),
        migrations.CreateModel(
            name='Number',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, unique=True, verbose_name='Номер телефона')),
                ('atc', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='leads.atc', verbose_name='ATC')),
            ],
        ),
        migrations.CreateModel(
            name='Lead',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mac_address', models.CharField(blank=True, max_length=12, validators=[django.core.validators.RegexValidator(code='invalid', flags=re.RegexFlag['IGNORECASE'], inverse_match=False, message='Не правильный ввод, пример ввода: 2c549188c9e3', regex='^([0-9a-f]{2}){5}([0-9a-f]{2})$')], verbose_name='MAC-Адрес')),
                ('first_name', models.CharField(max_length=20, verbose_name='Имя')),
                ('last_name', models.CharField(max_length=20, verbose_name='Фамилия')),
                ('patronymic_name', models.CharField(max_length=20, verbose_name='Отчество')),
                ('date_added', models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')),
                ('update_added', models.DateTimeField(auto_now_add=True, verbose_name='Дата изменения')),
                ('active', models.BooleanField(default=True)),
                ('reservation', models.BooleanField(default=False, verbose_name='Зарезервировать')),
                ('line', models.CharField(choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10')], default='1', max_length=5, verbose_name='Линия')),
                ('passwd', django_extensions.db.fields.ShortUUIDField(blank=True, default=shortuuid.main.ShortUUID.uuid, editable=False, unique=True, verbose_name='Пароль')),
                ('atc', models.ManyToManyField(to='leads.atc', verbose_name='ATC')),
                ('company', models.ManyToManyField(to='leads.company', verbose_name='Компания')),
                ('phone_model', models.ManyToManyField(to='leads.apparats', verbose_name='Модель телефона')),
                ('phone_number', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to='leads.number', verbose_name='Номер телефона')),
            ],
            options={
                'unique_together': {('mac_address', 'line')},
            },
        ),
    ]
