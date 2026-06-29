from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.validators import MinValueValidator

# ------------------------------------
# Modelos que sirven como catalogos
# ------------------------------------

# Modelo de los productos del sistema

class Producto(models.Model):
    TIPOS_PRODUCTO = [
        ('OLLA', 'Olla Individual'),
        ('SET', 'Set Completo'),
        ('REPUESTO', 'Repuesto'),
    ]
    codigo_sku = models.CharField(max_length=50, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPOS_PRODUCTO, default='OLLA')
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    categoria = models.CharField(max_length=50, help_text="Categoría o familia del producto (opcional)", choices=[
        ('GAMA_ALTA', 'Premium / Confort'),
        ('GAMA_MEDIA', 'Estándar / Familiar'),
        ('GAMA_BAJA', 'Escencial / Económica'),
    ])

    def __str__(self):
        return f"{self.codigo_sku} - {self.nombre} ({self.get_categoria_display()})"

# Modelo de los planes de pago a plazas

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

# Modelo de las etiquetas de severidad para el scoring de riesgo

class CategoriaRiesgo(models.Model):
    opciones_codigo = ['ACEPTABLE', 'MEDIO', 'CRITICO'] 
    codigo = models.CharField(max_length=20, unique=True, choices=[(opcion, opcion.upper()) for opcion in opciones_codigo], help_text="Seleccione el nivel de riesgo")
    descripcion = models.CharField(max_length=255)
    factor_severidad = models.FloatField(help_text="Multiplicador para el cálculo del scoring")

    class Meta:
        verbose_name = 'Categoría de Riesgo'
        verbose_name_plural = 'Categorías de Riesgo'

    def __str__(self):
        return f"{self.codigo} (Factor: {self.factor_severidad})"

# Modelo de las estrategias para mejorar la situación de mora de un cliente (Repositorio CBR)

class TecnicaMejora(models.Model):
    nombre = models.CharField(max_length=150, help_text="Ej: Reestructuración de Cuota, Llamada Persuasiva")
    descripcion = models.TextField()

    class Meta:
        verbose_name = 'Técnica de Mejora'
        verbose_name_plural = 'Técnicas de Mejora'

    def __str__(self):
        return self.nombre

# --------------------------------
# Modelo del sujeto de analisis
# --------------------------------

# Modelo del cliente, que es el sujeto de análisis del sistema de scoring y gestión de mora

class Cliente(models.Model):
    CATEGORIAS_RIESGO = [
        ('ACEPTABLE', 'Aceptable'),
        ('MEDIO', 'Medio'),
        ('CRITICO', 'Crítico'),
    ]
    identificacion = models.CharField(max_length=15, unique=True)
    nombres = models.CharField(max_length=150)
    incidencias_mora_total = models.IntegerField(default=0)
    categoria_riesgo = models.ForeignKey(CategoriaRiesgo, on_delete=models.PROTECT)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return f"{self.nombres} - {self.identificacion} - Riesgo Actual: {self.categoria_riesgo.codigo if self.categoria_riesgo else 'Sin Categoría'}"

# Modelo del perfil socioeconomico del cliente, que se puede usar para alimentar el motor de scoring con más variables (opcional)

class PerfilSocioeconomico(models.Model):
    ESTADOS_CIVILES = [
        ('SOLTERO', 'Soltero/a'), 
        ('CASADO', 'Casado/a'), 
        ('DIVORCIADO', 'Divorciado/a'), 
        ('UNION_LIBRE', 'Unión Libre')
    ]
    NIVELES_ESTUDIO = [
        ('PRIMARIA', 'Primaria'), 
        ('SECUNDARIA', 'Secundaria'), 
        ('TERCER_NIVEL', 'Tercer Nivel / Grado'), 
        ('CUARTO_NIVEL', 'Posgrado')
    ]
    TIPOS_TRABAJO = [
        ('DEPENDIENTE', 'Empleado Público/Privado'), 
        ('INDEPENDIENTE', 'Comerciante / Empresario'), 
        ('INFORMAL', 'Actividades Informales'), 
        ('DESEMPLEADO', 'Sin Empleo Fijo')
    ]

    cliente = models.OneToOneField(Cliente, on_delete=models.CASCADE, related_name='perfil_socioeconomico')
    estado_civil = models.CharField(max_length=20, choices=ESTADOS_CIVILES)
    tiene_hijos = models.BooleanField(default=False)
    numero_hijos = models.PositiveIntegerField(default=0)
    tipo_trabajo = models.CharField(max_length=20, choices=TIPOS_TRABAJO)
    ingreso_mensual = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    gastos_fijos_estimados = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    nivel_estudio = models.CharField(max_length=20, choices=NIVELES_ESTUDIO)

    class Meta:
        verbose_name = 'Perfil Socioeconómico'
        verbose_name_plural = 'Perfiles Socioeconómicos'

    def __str__(self):
        return f"Perfil de {self.cliente.nombres}"

# ---------------------------------------------------------------
# Modelos que no se van a utilizar especificamente para el CORE
# ---------------------------------------------------------------

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

# ------------------------------------
# Modelo para el contexto financiero
# ------------------------------------
    
# Modelo para ver el estado actual de la deuda

class Venta(models.Model):
    ESTADOS_VENTA = [
        ('PENDIENTE', 'Pendiente de Pago'),
        ('PAGADA', 'Pagada'),
        ('EN_MORA', 'En Mora'),
    ]
    
    # Se usaran mas adelante en el sistema para calcular las comisiones y los colaboradores
    colaborador = models.ForeignKey(Vendedor, on_delete=models.PROTECT, related_name='ventas_realizadas')
    comision_calculada = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='compras_realizadas')
    diferido = models.ForeignKey(Diferido, on_delete=models.PROTECT, null=True, blank=True, related_name='ventas_asociadas')
    numero_cuotas_pactadas = models.IntegerField(default=1, help_text="1 si es pago al contado, más de 1 si es a plazo")
    valor_mensualidad = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    total_pagar = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    fecha_emision = models.DateField(auto_now_add=True)
    descripcion_venta = models.CharField(max_length=255, blank=True, null=True, help_text="Descripción breve de la venta")
    estado_pago = models.CharField(max_length=20, choices=ESTADOS_VENTA, default='PENDIENTE')
    
    def save(self, *args, **kwargs):
                
        if self.total_pagar is not None and self.numero_cuotas_pactadas:
            if self.numero_cuotas_pactadas > 0:
                # Realizamos la división y redondeamos a 2 decimales exactos
                mensualidad_calculada = self.total_pagar / self.numero_cuotas_pactadas
                self.valor_mensualidad = round(mensualidad_calculada, 2)
            else:
                # Protección por si intentan guardar con 0 cuotas
                self.valor_mensualidad = self.total_pagar
        else:
            self.valor_mensualidad = Decimal('0.00')
            
        # Ejecutamos el guardado original de Django
        super().save(*args, **kwargs)
    
    class Meta: 
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-fecha_emision']
        
    def __str__(self):
        return f"Venta #{self.id} a {self.cliente.nombres} - Total: {self.total_pagar} - Estado: {self.estado_pago}"

# Modelo para guardar el detalle de cada venta en base al producto, permitiendo tener un registro exacto de qué productos se vendieron en cada transacción

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

# ------------------------------------------
# Modelo para la memoria del core
# ------------------------------------------

class HistorialGestion(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='historial_gestiones')
    tecnica = models.ForeignKey(TecnicaMejora, on_delete=models.PROTECT)
    fecha_aplicacion = models.DateField(auto_now_add=True)
    fue_exitosa = models.BooleanField(default=False, help_text="¿La técnica logró regularizar al cliente?")
    observaciones = models.TextField(blank=True, null=True)
    mensualidad_en_mora = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Monto de la mensualidad que estaba en mora al momento de aplicar la técnica")
    diferido_sugerido_meses = models.PositiveIntegerField(default=0, help_text="En caso de sugerir un plan de pago a plazo, indique la cantidad de meses recomendada")

    class Meta:
        verbose_name = 'Historial de Gestión'
        verbose_name_plural = 'Historiales de Gestión'

    def __str__(self):
        return f"Gestión a {self.cliente.nombres} - Éxito: {self.fue_exitosa}"

