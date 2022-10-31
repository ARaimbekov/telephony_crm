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
import shortuuid



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
    mac_address = models.CharField(max_length=12,blank=True, verbose_name='MAC-Адрес')
    # mac_address = models.CharField(max_length=12,blank=True, verbose_name='MAC-Адрес', validators = [
    #     RegexValidator(
    #         regex=r'^([0-9a-f]{2}){5}([0-9a-f]{2})$',
    #         message = 'Не правильный ввод, пример ввода: 2c549188c9e3',
    #         code = 'invalid',
    #         inverse_match = False,
    #         flags = re.IGNORECASE
    #     )
    # ])
    first_name = models.CharField(max_length=20, verbose_name='Имя')
    last_name = models.CharField(max_length=20, verbose_name='Фамилия')
    patronymic_name = models.CharField(max_length=20, verbose_name='Отчество')
    phone_model = models.ManyToManyField("Apparats", verbose_name='Модель телефона')
    company = models.ManyToManyField("company", verbose_name='Компания')
    date_added = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    update_added = models.DateTimeField(auto_now_add=True, verbose_name='Дата изменения')
    active = models.BooleanField(default=True)
    reservation = models.BooleanField(default=False, verbose_name='Зарезервировать')
    line = models.CharField(max_length=5,choices=CHOICES, default='1', verbose_name='Линия')
    atc = models.ManyToManyField("atc", verbose_name='ATC')
    passwd = ShortUUIDField(max_length=22, unique=True, editable=False, default=shortuuid.uuid, verbose_name='Пароль')

    class Meta:
        unique_together = ['mac_address', 'line']


    objects = LeadManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


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
    ip_address = models.CharField(max_length=30, unique=True, verbose_name='IP адрес')

    def __str__(self):
        return self.name

