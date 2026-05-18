from decimal import Decimal
from django.utils import timezone
from .models import CategoriaRiesgo, Cliente, Diferido, TecnicaMejora, HistorialGestion, Venta, Vendedor, Producto


# ===============================================
# 1. CÁLCULO Y ASIGNACIÓN DE CATEGORÍA RIESGO 
# ===============================================

def calcular_scoring_riesgo(cliente):

    #Calculo para evitar division en 0 para el nivel de riesgo
    total_diferidos = cliente.compras_realizadas.count()
    if total_diferidos == 0:
        return 
    
    #Variable para encontrar la categoria del cliente
    factor = cliente.categoria_riesgo.factor_severidad if cliente.categoria_riesgo else 1.0
    
    #Caculo de nivel de riesgo
    score = (cliente.incidencias_mora_total / total_diferidos) * factor

    #Asignación de categoría de riesgo según el score calculado
    if score > 0.8:
        cliente.categoria_riesgo = CategoriaRiesgo.objects.get(codigo='CRITICO')
    elif score > 0.4:
        cliente.categoria_riesgo = CategoriaRiesgo.objects.get(codigo='MEDIO')
    else:
        cliente.categoria_riesgo = CategoriaRiesgo.objects.get(codigo='ACEPTABLE')
    cliente.save()
    
# ===============================================
# 2. CÁLCULO DE COMISIONES
# ===============================================

def calcular_comision_vendedor(venta):
    
    # 1. Obtenemos el precio total del producto 
    monto_venta = Decimal(str(venta.producto.precio))
    
    # 2. Definimos una comisión base estándar (5% de la venta)
    porcentaje_base = Decimal('0.05')
    
    # 3. Aplicamos modificadores de comisión según el riesgo del cliente
    riesgo_cliente = venta.cliente.categoria_riesgo.codigo if venta.cliente.categoria_riesgo else 'ACEPTABLE'
    
    if riesgo_cliente == 'ACEPTABLE':
        # Bono del 2% extra por venderle a un cliente seguro
        modificador = Decimal('0.02') 
    elif riesgo_cliente == 'MEDIO':
        # No hay bono, comisión estándar
        modificador = Decimal('0.00') 
    elif riesgo_cliente == 'CRITICO':
        # Penalización: se le quita un 3% de comisión por arriesgar a la empresa
        modificador = Decimal('-0.03') 
        
    # 4. Cálculo final
    porcentaje_final = porcentaje_base + modificador
    comision_calculada = monto_venta * porcentaje_final
    
    # Retornamos el valor redondeado a 2 decimales
    return round(comision_calculada, 2)