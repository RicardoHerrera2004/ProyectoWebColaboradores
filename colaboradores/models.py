from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

#Modelo: Producto
class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)

    def __str__(self):
        return self.nombre

#Prueba de Login Personalizado
class UsuarioVIP(models.Model):
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255) 

    def __str__(self):
        return self.username