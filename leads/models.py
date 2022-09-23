from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    is_organisor = models.BooleanField(default=True)
    is_agent = models.BooleanField(default=False)


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username


class LeadManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()


class Lead(models.Model):
    phone_number = models.OneToOneField("Number", on_delete=models.PROTECT, verbose_name='Номер телефона')     
    mac_address = models.CharField(max_length=15, verbose_name='MAC-Адрес')    
    first_name = models.CharField(max_length=20, verbose_name='Имя')
    last_name = models.CharField(max_length=20, verbose_name='Фамилия')
    patronymic_name = models.CharField(max_length=20, verbose_name='Отчество')
    phone_model = models.ManyToManyField("Apparats",  verbose_name='Модель телефона')
    # Company = models.CharField(max_length=50, verbose_name='Компания')
    Company = models.ManyToManyField("Company", verbose_name='Компания')
    date_added = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    update_added = models.DateTimeField(auto_now_add=True, verbose_name='Дата изменения')
    agent = models.ForeignKey("Agent", null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Оператор')
    active = models.BooleanField(default=True)

    age = models.IntegerField(default=0)
    organisation = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    category = models.ForeignKey("Category", related_name="leads", null=True, blank=True, on_delete=models.SET_NULL)
    description = models.TextField()
    email = models.EmailField()
    profile_picture = models.ImageField(null=True, blank=True, upload_to="profile_pictures/")
    converted_date = models.DateTimeField(null=True, blank=True)
    


    objects = LeadManager()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Company(models.Model):
    name = models.CharField(max_length=50, verbose_name='компании')

    def __str__(self):
        return self.name


class Apparats(models.Model):
    name = models.CharField(max_length=50, verbose_name='модель')

    def __str__(self):
        return self.name


class Number(models.Model):
    name = models.CharField(max_length=30, verbose_name='Номер телефона 2')

    def __str__(self):
        return self.name


def handle_upload_follow_ups(instance, filename):
    return f"lead_followups/lead_{instance.lead.pk}/{filename}"


class FollowUp(models.Model):
    lead = models.ForeignKey(Lead, related_name="followups", on_delete=models.CASCADE)
    date_added = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    file = models.FileField(null=True, blank=True, upload_to=handle_upload_follow_ups)

    def __str__(self):
        return f"{self.lead.first_name} {self.lead.last_name}"


class Agent(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organisation = models.ForeignKey(UserProfile, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user}"


class Category(models.Model):
    name = models.CharField(max_length=30)  # New, Contacted, Converted, Unconverted
    organisation = models.ForeignKey(UserProfile, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


def post_user_created_signal(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


post_save.connect(post_user_created_signal, sender=User)