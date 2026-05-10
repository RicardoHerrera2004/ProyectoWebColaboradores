from django.contrib import admin
from .models import Producto, Vendedor, Venta

# Clases Registradas
admin.site.register(Producto)
admin.site.register(Vendedor)
admin.site.register(Venta)