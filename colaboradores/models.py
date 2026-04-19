from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.validators import MinValueValidator

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
    
#Modelo: Vendedor
class Vendedor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nombre_completo = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Vendedor'
        verbose_name_plural = 'Vendedores'
        ordering = ['nombre_completo']

    def __str__(self):
        return self.nombre_completo
    
#Modelo: Regla del negocio
class ReglaNegocio(models.Model):
    porcentaje = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=[
            MinValueValidator(Decimal('0.01'))],
        help_text="Porcentaje de descuento aplicado a las ventas (ej: 10.00 para el 10%)"
    )
    
    monto_minimo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal('0.01'))],
        help_text="Monto mínimo de venta para aplicar el descuento"
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Regla de Negocio'
        verbose_name_plural = 'Reglas de Negocio'
        ordering = ['monto_minimo']
        
    def __str__(self):
        return f"Regla {self.id}: {self.porcentaje}% descuento para ventas >= {self.monto_minimo}"
    
    def porcentaje_decimal(self):
        return self.porcentaje / Decimal('100')
    
#Modelo: Venta
class Venta(models.Model):
    vendedor = models.ForeignKey(
        Vendedor, 
        on_delete=models.CASCADE, 
        related_name='ventas'
    )
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.CASCADE,
        related_name='ventas'
    )
    cantidad = models.IntegerField()
    monto = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    fecha_venta = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-fecha_venta']
    
    def __str__(self):
        return f"Venta {self.id} - {self.producto.nombre} x{self.cantidad} por {self.vendedor.nombre_completo}"
    
    def calcular_comision(self):
        reglas_activas = ReglaNegocio.objects.filter(activa=True, monto_minimo__lte=self.monto).order_by('-monto_minimo')
        if reglas_activas.exists():
            regla_aplicable = reglas_activas.first()
            return self.monto * regla_aplicable.porcentaje_decimal()
        return Decimal('0.00')
    
#Clase: ComisionCalculada
class ComisionCalculada(models.Model):
    venta = models.OneToOneField(Venta, on_delete=models.CASCADE, related_name='comision')
    monto_comision = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_calculo = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Comisión Calculada'
        verbose_name_plural = 'Comisiones Calculadas'
        ordering = ['-fecha_calculo']
    
    def __str__(self):
        return f"Comisión para Venta {self.venta.id}: {self.monto_comision}"
        