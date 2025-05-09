from email.policy import default
from random import choices
from secrets import choice
from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
import re, uuid 
from uuid import uuid4
from django_extensions.db.fields import ShortUUIDField
from django.core.validators import MinLengthValidator
import shortuuid
import datetime



class User(AbstractUser):
    is_organisor = models.BooleanField(default=True)


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='Пользователь')

    def __str__(self):
        return self.user.username


class LeadManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()


class Lead(models.Model):

    TIMEZONE_CHOICES = (
        ('+8', 'Иркутск +8'),
        ('+3', 'Москва +3'),
        ('+7', 'Новосибирск +7'),
        ('+9', 'Якутск +9'),
    )
    CHOICES = (
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10'),
    )

    phone_number = models.OneToOneField("Number", unique=True, on_delete=models.PROTECT, verbose_name='Номер телефона')    
    mac_address = models.CharField(max_length=17, blank=True, verbose_name='MAC-Адрес', validators=[MinLengthValidator(12)])
    # mac_address = models.CharField(max_length=17,blank=True, verbose_name='MAC-Адрес', validators = [
    #     RegexValidator(
    #         regex=r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$',
    #         message = 'Не правильный ввод, пример ввода: 2c549188c9e3',
    #         code = 'invalid',
    #         inverse_match = False,
    #         flags = re.IGNORECASE
    #     )
    # ])
    first_name = models.CharField(max_length=20, blank=True, verbose_name='Имя')
    last_name = models.CharField(max_length=20, verbose_name='Фамилия')
    patronymic_name = models.CharField(max_length=20, blank=True, verbose_name='Отчество')
    phone_model = models.ManyToManyField("Apparats", verbose_name='Модель телефона')
    company = models.ManyToManyField("company", verbose_name='Компания')
    date_added = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    update_added = models.DateTimeField(auto_now=True, verbose_name='Дата изменения')
    active = models.BooleanField(default=True)
    reservation = models.BooleanField(default=False, verbose_name='Зарезервировать')
    line = models.CharField(max_length=5,choices=CHOICES, default='1', verbose_name='Линия')
    atc = models.ManyToManyField("atc", verbose_name='ATC')
    passwd = ShortUUIDField(max_length=22, editable=False, default=shortuuid.uuid, verbose_name='Пароль')
    updated_user = models.CharField(max_length=20, blank=True, verbose_name='Обновил')
    created_user = models.CharField(max_length=20, blank=True, verbose_name='Добавил')
    record_calls = models.BooleanField(default=False, verbose_name='Запись разговоров') 
    external_line_access = models.CharField(
        max_length=20,
        choices=[
            ('локальные_МГ', 'Локальные МГ'),
            ('локальные_МГ_МН', 'Локальные МГ и МН'),
            ('локальные', 'Локальные'),
        ],
        default='локальные_МГ',
        verbose_name='Доступ к внешним линиям'
    )  # Выпадающий список
    call_forwarding = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^\d{0,11}$', message="Поле должно содержать только цифры и быть не длиннее 11 символов.")],
        verbose_name='Переадресация'
    )  # Текстовое поле для переадресации

    timezone = models.CharField(
    max_length=3,
    choices=TIMEZONE_CHOICES,
    default='+8',  # Значение по умолчанию - Иркутск
    verbose_name='Часовой пояс'
    )

    class Meta:
        unique_together = ['mac_address', 'line']


    objects = LeadManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name} {self.phone_number}"


class Company(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='Компании')

    def __str__(self):
        return self.name


class Apparats(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='Модель')

    def __str__(self):
        return self.name


class Number(models.Model):
    name = models.CharField(max_length=30, unique=True, verbose_name='Номер телефона')
    atc = models.ForeignKey('atc', on_delete=models.PROTECT, verbose_name='ATC')

    def __str__(self):
        return self.name


class Atc(models.Model):
    name = models.CharField(max_length=30, unique=True, verbose_name='Наименование')
    ip_address = models.CharField(max_length=30, verbose_name='IP адрес')

    def __str__(self):
        return self.name

