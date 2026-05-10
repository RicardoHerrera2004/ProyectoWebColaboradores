from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.validators import MinValueValidator

# MODELOS DE ADMINISTRACIÓN Y CORE CBR 

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


# MODELOS ORIGINALES DE LOS COLABORADORES

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
    
class Venta(models.Model):
    # Opciones predefinidas para el estado de la venta, evitando inputs manuales
    ESTADOS_PAGO = [
        ('AL_DIA', 'Al Día'),
        ('EN_MORA', 'En Mora (Riesgo)'),
        ('CANCELADO', 'Pagado en su totalidad'),
    ]
    
    colaborador = models.ForeignKey(Vendedor, on_delete=models.PROTECT, related_name='ventas_realizadas')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='compras_realizadas')
    
    # El diferido puede ser nulo si la venta es al contado (Riesgo Crítico)
    diferido = models.ForeignKey(Diferido, on_delete=models.PROTECT, null=True, blank=True)
    
    fecha_emision = models.DateTimeField(auto_now_add=True)
    total_pagar = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    estado_pago = models.CharField(max_length=20, choices=ESTADOS_PAGO, default='AL_DIA')
    
    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-fecha_emision']
    
    def __str__(self):
        return f"Venta #{self.id} - Cliente: {self.cliente.nombres} - Total: ${self.total_pagar}"

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    
    cantidad = models.IntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        verbose_name = 'Detalle de Venta'
        verbose_name_plural = 'Detalles de Ventas'
        
    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre} (Venta #{self.venta.id})"