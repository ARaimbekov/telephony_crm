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
import secrets
from django.conf import settings


class EmployeeDwh(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Активен"
        DELETED = "deleted", "Удалён в источнике"
        DISABLED = "disabled", "Отключён"
        OTHER = "other", "Другое"

    guid_nsi = models.UUIDField(unique=True, db_index=True)

    full_name = models.CharField(max_length=255, blank=True)
    samaccountname = models.CharField(max_length=150, db_index=True)
    mail = models.EmailField(max_length=254, blank=True)

    company = models.CharField(max_length=255, blank=True)
    department = models.CharField(max_length=255, blank=True)
    job_title = models.CharField(max_length=255, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    source_last_seen_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} ({self.samaccountname})"

class User(AbstractUser):
    is_organisor = models.BooleanField(default=True)


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='Пользователь')

    def __str__(self):
        return self.user.username


class LeadManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()


class ApiToken(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название токена")
    token = models.CharField(max_length=128, unique=True, db_index=True, verbose_name="Токен", blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Кем создан"
    )

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(48)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


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
    display_name = models.CharField(max_length=100, blank=True, verbose_name="Отображаемое имя")
    patronymic_name = models.CharField(max_length=20, blank=True, verbose_name='Отчество')
    phone_model = models.ManyToManyField("Apparats", verbose_name='Модель телефона')
    company = models.ManyToManyField("company", verbose_name='Компания')
    date_added = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    update_added = models.DateTimeField(auto_now=True, verbose_name='Дата изменения')
    active = models.BooleanField(default=True)
    reservation = models.BooleanField(default=False, verbose_name='Зарезервировать')
    line = models.CharField(max_length=5,choices=CHOICES, default='1', verbose_name='Линия')
    atc = models.ManyToManyField("atc", verbose_name='ATC')
    passwd = ShortUUIDField(max_length=32, editable=False, default=shortuuid.uuid, verbose_name='Пароль')
    updated_user = models.CharField(max_length=20, blank=True, verbose_name='Обновил')
    created_user = models.CharField(max_length=20, blank=True, verbose_name='Добавил')
    record_calls = models.BooleanField(default=False, verbose_name='Запись разговоров')
    employees = models.ManyToManyField(
        EmployeeDwh,
        blank=True,
        related_name="leads",
        verbose_name="Сотрудники (DWH)"
    ) 
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

    @staticmethod
    def employee_display_name(employee):
        parts = (employee.full_name or "").strip().split()
        if not parts:
            return ""

        last_name = parts[0]
        initials = "".join(part[0].upper() for part in parts[1:3] if part)
        if initials:
            return f"{last_name} {initials}"
        return last_name

    @property
    def generated_display_name(self):
        employee = next(iter(self.employees.all()), None) if self.pk else None
        if not employee:
            return ""
        return self.employee_display_name(employee)

    @property
    def has_manual_display_name(self):
        return bool((self.display_name or "").strip())

    @property
    def actual_display_name(self):
        if self.has_manual_display_name:
            return self.display_name.strip()
        return self.generated_display_name

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
