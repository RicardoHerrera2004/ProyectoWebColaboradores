from django.contrib import admin
from .models import Producto, Vendedor, Venta, ComisionCalculada, ReglaNegocio

# Clases Registradas
admin.site.register(Producto)
admin.site.register(Vendedor)
admin.site.register(Venta)
admin.site.register(ComisionCalculada)
admin.site.register(ReglaNegocio)