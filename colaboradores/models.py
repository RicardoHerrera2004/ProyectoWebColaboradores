from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.validators import MinValueValidator

# ==========================================
# 1. MODELOS DE ADMINISTRACIÓN Y CORE CBR (NUEVOS)
# ==========================================

class CategoriaRiesgo(models.Model):
    codigo = models.CharField(max_length=20, unique=True, help_text="Ej: ACEPTABLE, MEDIO, CRITICO")
    descripcion = models.CharField(max_length=255)
    factor_severidad = models.FloatField(help_text="Multiplicador para el cálculo del scoring")

    class Meta:
        verbose_name = 'Categoría de Riesgo'
        verbose_name_plural = 'Categorías de Riesgo'

    def __str__(self):
        return f"{self.codigo} (Factor: {self.factor_severidad})"

class Diferido(models.Model):
    meses_plazo = models.IntegerField()
    porcentaje_interes = models.DecimalField(max_digits=5, decimal_places=2)
    requiere_entrada = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Plan Diferido'
        verbose_name_plural = 'Planes Diferidos'
        ordering = ['meses_plazo']

    def __str__(self):
        return f"{self.meses_plazo} meses al {self.porcentaje_interes}%"

class TecnicaMejora(models.Model):
    nombre = models.CharField(max_length=150, help_text="Ej: Reestructuración de Cuota, Llamada Persuasiva")
    descripcion = models.TextField()

    class Meta:
        verbose_name = 'Técnica de Mejora'
        verbose_name_plural = 'Técnicas de Mejora'

    def __str__(self):
        return self.nombre

class Cliente(models.Model):
    identificacion = models.CharField(max_length=15, unique=True)
    nombres = models.CharField(max_length=150)
    incidencias_mora_total = models.IntegerField(default=0)
    categoria_riesgo = models.ForeignKey(CategoriaRiesgo, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return f"{self.nombres} - {self.identificacion}"

class HistorialGestion(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='historial_gestiones')
    tecnica = models.ForeignKey(TecnicaMejora, on_delete=models.PROTECT)
    fecha_aplicacion = models.DateField(auto_now_add=True)
    fue_exitosa = models.BooleanField(default=False, help_text="¿La técnica logró regularizar al cliente?")
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Historial de Gestión'
        verbose_name_plural = 'Historiales de Gestión'

    def __str__(self):
        return f"Gestión a {self.cliente.nombres} - Éxito: {self.fue_exitosa}"


# ==========================================
# 2. TUS MODELOS ORIGINALES (CON LIGEROS AJUSTES)
# ==========================================

class Producto(models.Model):
    TIPOS_PRODUCTO = [
        ('OLLA', 'Olla Individual'),
        ('SET', 'Set Completo'),
        ('REPUESTO', 'Repuesto'),
    ]
    codigo_sku = models.CharField(max_length=50, unique=True, null=True, blank=True) # Añadido por el PDF
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPOS_PRODUCTO, default='OLLA') # Añadido por el PDF
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.codigo_sku} - {self.nombre}"

class UsuarioVIP(models.Model):
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255) 

    def __str__(self):
        return self.username
    
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
    
class ReglaNegocio(models.Model):
    porcentaje = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Porcentaje de descuento aplicado a las ventas (ej: 10.00 para el 10%)"
    )
    monto_minimo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
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
    
class Venta(models.Model):
    vendedor = models.ForeignKey(Vendedor, on_delete=models.CASCADE, related_name='ventas')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='ventas')
    # Opcional: podrías relacionar la venta con el Cliente y el Diferido según tu diagrama PDF
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, null=True, blank=True)
    diferido = models.ForeignKey(Diferido, on_delete=models.PROTECT, null=True, blank=True)
    
    cantidad = models.IntegerField()
    monto = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
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