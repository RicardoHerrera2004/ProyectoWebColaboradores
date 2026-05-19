from decimal import Decimal
from django.db.models import Count
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
    monto_venta = Decimal(str(venta.total_pagar))
    
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
    
#================================================
# 3. MOTOR CBR DE RECOMENDACIÓN DE TÉCNICA DE COBRANZA 
#================================================

def motor_cbr_recomendar_tecnica(cliente_actual):
    
    # Encontramos la categoria actual del cliente
    categoria_actual = cliente_actual.categoria_riesgo
    
    # Si el cliente es nuevo o no tiene riesgo calculado, no hay nada que predecir
    if not categoria_actual:
        return {
            'recomendacion': 'Sin datos de riesgo',
            'mensaje': 'El cliente no tiene un perfil de riesgo asignado por el motor.',
            'confianza': 0
        }

    # Buscamos gestiones EXITOSAS en clientes del MISMO RIESGO
    gestiones_similares = HistorialGestion.objects.filter(
        cliente__categoria_riesgo=categoria_actual,
        fue_exitosa=True 
    )

    # Si el sistema está vacío o no hay éxitos previos en este perfil, sugerimos la técnica estándar y explicamos la falta de data
    if not gestiones_similares.exists():
        return {
            'recomendacion': 'Contacto Telefónico Básico',
            'mensaje': 'No hay data histórica suficiente para este perfil de riesgo. Inicie con la técnica estándar.',
            'confianza': 0
        }

    # Agrupamos por técnica y ver cuál ganó más veces
    ranking_tecnicas = gestiones_similares.values('tecnica__nombre').annotate(
        total_exitos=Count('id')
    ).order_by('-total_exitos')

    # Extraemos al ganador absoluto
    mejor_tecnica = ranking_tecnicas.first()
    
    # Calculamos la matemática de confianza (Éxitos de esta técnica / Total de éxitos en este perfil)
    total_casos_exitosos = gestiones_similares.count()
    porcentaje_confianza = round((mejor_tecnica['total_exitos'] / total_casos_exitosos) * 100, 1)

    # Entregamos el dictamen de la sugerencia al controlador
    return {
        'recomendacion': mejor_tecnica['tecnica__nombre'],
        'mensaje': f"Basado en {mejor_tecnica['total_exitos']} casos de éxito en clientes con riesgo '{categoria_actual.codigo}'.",
        'confianza': porcentaje_confianza
    }