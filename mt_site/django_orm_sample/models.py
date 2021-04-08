from django.db import models


class Hospital(models.Model):
    name = models.CharField(max_length=100, unique=True)
    address = models.CharField(max_length=100)


class Patient(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=120)
