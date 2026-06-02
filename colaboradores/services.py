from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from django.db.models import Count
from django.core.exceptions import ObjectDoesNotExist
from .models import Cliente, Venta, DetalleVenta, Diferido, Producto, TecnicaMejora, HistorialGestion, CategoriaRiesgo, PerfilSocioeconomico
import math

# =============================================================================
# ESTRUCTURAS DE DATOS (DTOs) Y CLASES DE SERVICIO PARA EL CORE ANALÍTICO
# =============================================================================

# Deuda actual del cliente
@dataclass
class PerfilRiesgo:
    score_bruto: float
    score_porcentaje: float                        
    categoria_sugerida: str
    factores: dict
    confianza: float

# Variable para guardar clientes con similitudes
@dataclass
class CasoSimilar:
    historial: HistorialGestion
    similitud: float
    factores_coicidencias: list

# Recomendación de técnica de cobranza según perfil de riesgo
@dataclass
class RecomendacionTecnica:
    tecnica: TecnicaMejora
    confianza: float
    tasa_exito_historica: float
    casos_similares_usados: int
    razonamiento: str
    
# Recomendación de diferidos optimizados según capacidad de pago y riesgo
@dataclass
class RecomendacionDiferido:
    diferido: Diferido
    cuota_estimada: Decimal
    porcentaje_sobre_capacidad: float
    viable: bool
    nivel_riesgo: str
    razon: str
    
# Recomendación de productos financieros según perfil socioeconómico y riesgo
@dataclass
class RecomendacionProducto:
    producto: Producto
    puntuacion: float
    razon: str
    
# Agrupacion completa de análisis para un cliente en mora, entregada al controlador para mostrar 
@dataclass
class AnalisisCompleto:
    cliente: Cliente
    perfil_riesgo: PerfilRiesgo
    tecnicas_recomendadas: list
    diferidos_recomendados: list
    productos_recomendados: list
    monto_total_mora: Decimal
    resumen_ejecutivo: str

# ===============================================================
# Motor Scoring Multifactor para evaluar riesgo actual
# ===============================================================

class ScoringEngine:
    # Constantes
    PESOS = {
        'tasa_mora': 0.35,           # 35% de peso a la tasa de mora, ya que un cliente que siempre paga tarde es más riesgoso
        'recencia_mora': 0.3,        # 30% de peso a la recencia, ya que un cliente que acaba de caer en mora es más riesgoso que uno que no paga hace años pero ya se estabilizó
        'carga_financiera': 0.2,     # 20% de peso a la carga financiera, ya que un cliente con muchas deudas activas es más riesgoso
        'concentracion': 0.15        # 15% de peso a la concentración, ya que un cliente que tiene toda su deuda en un solo producto es más riesgoso que uno que tiene deudas diversificadas 
    }
    
    UMBRAL = {
        'CRITICO': 0.65,             # Más del 65% de score es crítico
        'MEDIO': 0.35,               # Entre 35% y 65% es medio
    }
    
    # Calculo del perfil riesgo en tiempo real del cliente
    def calcular(self, cliente: Cliente) -> PerfilRiesgo:
        
        ventas = list(cliente.compras_realizadas.select_related('diferido').all())
        total = len(ventas)
        
        # Si el cliente es nuevo y no tiene historial, el riesgo es nulo y evitamos division por 0
        if total == 0:
            return PerfilRiesgo(
                score_bruto=0.0,
                score_porcentaje=0.0,
                categoria_sugerida='ACEPTABLE',
                factores={},
                confianza=0.0   
            )
        
        # Creacion de lista que recorre todas las compras del cliente que contengan Mora
        en_mora = []
        for v in ventas:
            if v.estado_pago == 'EN_MORA':
                en_mora.append(v)
         
        # Ejecucion de las 4 constantes en base al cliente en analiss       
        factores = {
            'tasa_mora': self._tasa_mora(en_mora, total),                  # Cantidad de compras impagadas / numero de compras totales
            'recencia_mora': self._recencia_mora(ventas, total),            # Todas las compras del historial, ordenarlas de las mas nueva a la mas vieja y revisar las ultimas 5
            'carga_financiera': self._carga_financiera(cliente, ventas),    # Objeto Cliente para ver cuanto gana al mes y el valor de todas las cuotas activas
            'concentracion': self._concentracion_mora(en_mora)              # Lista de compras impagadas para revisar los identificadores de los diferidos
        }
        
        score_base = sum(factores[clave] * self.PESOS[clave]        # Suma total de la multiplicacion de la nota del cliente x el PESO que le corresponde
                         for clave in self.PESOS)                   # Recorre las claves de la constante PESOS en "clave"
        
        # Ajuste por categoría de riesgo actual para evitar saltos bruscos en clientes que ya tienen un perfil definido
        sev = cliente.categoria_riesgo.factor_severidad if cliente.categoria_riesgo else 1.0
        
        # El score ajustado se limita a 1.0 (100%) para evitar valores extremos, y se le aplica un factor de severidad 
        score_ajustado = min(score_base * sev, 1.0)
        
        # Asignacion de la nueva categoria riesgo al cliente
        if score_ajustado >= self.UMBRAL['CRITICO']:
            categoria = 'CRITICO'
        elif score_ajustado >= self.UMBRAL['MEDIO']:
            categoria = 'MEDIO'
        else:
            categoria = 'ACEPTABLE'

        # Calculo de la confianza
        confianza = round(min(total / 8.0, 1.0), 4)   # Se define que haya recaido en el impago al menos 8 veces
        
        return PerfilRiesgo(
            score_bruto=round(score_base, 4),
            score_porcentaje=round(score_ajustado * 100, 2),
            categoria_sugerida=categoria, 
            factores={k.replace('_', ' ').title(): round(v * 100, 4) for k, v in factores.items()},
            confianza=confianza 
            # Redondeo de factores para evitar mostrar decimales infinitos
            # factores_limpios = {}                     Toma el diccionario original con los valores
            # for k, v in factores.items():             k = nombre del factor y v = valor del factor
            #   factores_limpios[k] = round(v, 4)

            # return PerfilRiesgo(
            #   ...
            # factores=factores_limpios,
            #   ...
            # )
            

        )

    # Calculo de la recencia de mora, dando mas peso a las compras mas recientes
    def _tasa_mora(self, en_mora: list, total: int) -> float:
        return len(en_mora) / total

    # Calculo de la recencia de mora, dando mas peso a las compras mas recientes
    def _recencia_mora(self, ventas: list, total: int) -> float:
        
        # llave=lambda, funcion desechable para ordenar las ventas por fecha de compra, de la mas nueva a la mas vieja
        # reverse = true para hacerle de la mas reciente
        recientes = sorted(ventas, key=lambda v: v.fecha_emision, reverse=True) [:5]  # Tomamos las 5 compras mas recientes para evaluar la recencia
        
        # Contamos cuantas de las compras recientes estan en mora y se suma
        mora_reciente = sum(1 for v in recientes if v.estado_pago == 'EN_MORA')
        
        # Retorna el porcentaje de compras recientes que estan en mora en base al total de compras, pero limitando el denominador a 5 para evitar penalizar demasiado a clientes con poco historial
        return mora_reciente / min(5, total)  

    # Calculo de la carga financiera, sumando el valor de las cuotas activas y comparandolo con los ingresos del cliente
    def _carga_financiera(self, cliente: Cliente, ventas: list) -> float:   
        try:
            
            # Primera extraccion si el cliente no tiene datos o los ingresos son negativos
            ingresos = float(cliente.perfil_socioeconomico.ingreso_mensual or 0)
            if ingresos <= 0:
                return 0.5
            
            gastos = float(cliente.perfil_socioeconomico.gastos_fijos_estimados or 0)
            
            # Filtras las ventas activas o en mora y suma las mensualidades
            activas = [venta for venta in ventas if venta.estado_pago in ['PENDIENTE', 'EN_MORA']]
            total_cuotas = sum(float(venta.valor_mensualidad) for venta in activas)
            
            carga_total_real = gastos + total_cuotas
            
            # Si paga más de lo que gana, satura en 1.0
            return min(carga_total_real / ingresos, 1.0)
            
        except (AttributeError, PerfilSocioeconomico.DoesNotExist):
            return 0.5 # Valor intermedio si no se puede calcular por falta de datos
        
    def _concentracion_mora(self, en_mora: list) -> float:
        
        # Si un cliente no tiene mora devuelve 0
        if not en_mora:
            return 0.0
        
        # Creacion de grupo de deudas
        grupos_deuda = {}
        
        # Se agrupa cada cuota impaga segun el plan al que pertenece
        for venta in en_mora:
            clave = (venta.diferido.id if venta.diferido else 'contado')
            grupos_deuda[clave] = grupos_deuda.get(clave, 0) + 1
            
        # Se define las variables totales para la ecuacion
        total_cuotas_impagas = len(en_mora)
        cantidad_planes_distintos = len(grupos_deuda)
        
        # Se calcula el indice sumando la fraccion al cuadrado de cada grupo
        # (Se utiliza la ecuacion economica matematica de: HHI = Suma de (numero de cuotas impagas / total_cuotas_impagas)^2)
        indice_concentracion = sum((count / total_cuotas_impagas) ** 2 for count in grupos_deuda.values())
        
        # Calculamos el minimo posible del indice
        indice_concentracion_minimo = 1 / cantidad_planes_distintos if cantidad_planes_distintos > 0 else 1.0
        
        # Si el indice de concentracion es igual al minimo, significa que el cliente tiene sus cuotas impagas perfectamente diversificadas entre varios planes, lo cual es positivo y se devuelve 0.0 para no penalizarlo
        if indice_concentracion_minimo >= 1.0:
            return 0.0
        
        # Normalizacion de la nota exacta entre 0.0 y 1.0
        nota_final_normalizada = (indice_concentracion - indice_concentracion_minimo) / (1 - indice_concentracion_minimo)
            
        return round(nota_final_normalizada, 4)
    
# ===============================================================
# MOTOR CBR CON INTELIGENCIA PREDICTIVA EN BASE A VECTORES
# ===============================================================

class CBREngine:
    
    def _vectorizar_perfil(self, cliente: Cliente) -> list:
    
        # Si el cliente no tiene datos se le ubica neutralmente (0,5)
        try: 
            perfil = cliente.perfil_socioeconomico
        except AttributeError:
            return [0.5, 0.5, 0.5, 0.5]
    
        ingreso_norm = min(float(perfil.ingreso_mensual or 0) / 3000.0, 1.0)  # Normalizamos a un máximo de $3000
    
        cargas_norm = min(perfil.numero_hijos / 5.0, 1.0)     # Normalizamos a un máximo de 5 cargas
    
        mapa_estudios = {
            'PRIMARIA': 0.25,
            'SECUNDARIA': 0.5,
            'TERCER_NIVEL': 0.75,
            'CUARTO_NIVEL': 1.0
        }
        estudios_norm = mapa_estudios.get(perfil.nivel_estudio, 0.5)  # Si no se especifica, se le da un valor intermedio
    
        mapa_civil = {
            'SOLTERO': 0.0,
            'DIVORCIADO': 0.4,
            'CASADO': 0.7,
            'UNION_LIBRE': 0.8
        }
    
        civil_norm = mapa_civil.get(getattr(perfil, 'estado_civil', ''), 0.5) # Protegido por si no existe
    
        # Retorno de los datos
        return [ingreso_norm, cargas_norm, estudios_norm, civil_norm]

    def _calcular_similitud(self, vec1: list, vec2: list) -> float:
    
        # Retomar y cancela si los vectores no tiene la misma longitud
        if len(vec1) != len(vec2):
            return 0.0
    
        # Se calcula la distancia entre los dos puntos en 4 dimensiones
        # Teorema de pitagoras
        suma_cuadrados = sum((a - b) ** 2 for a, b in zip(vec1, vec2))
        distancia = math.sqrt(suma_cuadrados)
    
        # Menor distancia = Mayor similitud
        distancia_maxima = math.sqrt(len(vec1))  # Distancia máxima posible en un espacio unitario
        distancia_normalizada = distancia / distancia_maxima 
    
        similitud = 1.0 - distancia_normalizada  # Similitud entre 0 y 1
    
        return round(similitud, 4)

    def recomendar_estrategia(self, cliente_actual: Cliente) -> RecomendacionTecnica:
        
        # Nucleo k-NN
        
        # Vectorizar al clilente que se esta analizando
        vector_actual = self._vectorizar_perfil(cliente_actual)
        
        # Extraer casos de exito
        casos_existosos = HistorialGestion.objects.filter(fue_exitosa=True).select_related('cliente', 'tecnica').all()
        
        casos_evaluados = []
        
        # Medicion de la distancia contra todos los clientes del pasado
        for caso in casos_existosos:
            
            # Se evita comparacion con el mismo cliente
            if caso.cliente.id == cliente_actual.id:
                continue
            
            vector_historico = self._vectorizar_perfil(caso.cliente)
            similitud = self._calcular_similitud(vector_actual, vector_historico)
            
            # Se guarda el resultado usando el DTO
            casos_evaluados.append(CasoSimilar(
                historial=caso,
                similitud=similitud,
                factores_coicidencias=[]
            ))
            
        # -- BLOQUE INDENTADO CORRECTAMENTE (FUERA DEL FOR) --
        
        # Si no hay datos para evaluar se aborta 
        if not casos_evaluados:
            return None
        
        # Se ordena de mayor a menor similitudes y nos quedamos con el top 3 (k=3)
        top_3_gemelos = sorted(casos_evaluados, key=lambda c: c.similitud, reverse=True)[:3]
        
        # Votacion de la mejor tecnica
        votos_tecnicas = {}
        for gemelo in top_3_gemelos:
            id_tecnica = gemelo.historial.tecnica.id
            votos_tecnicas[id_tecnica] = votos_tecnicas.get(id_tecnica, 0.0) + gemelo.similitud
            
        # Tecnica con mas votos
        id_tecnica_ganadora = max(votos_tecnicas, key=votos_tecnicas.get)
        
        # Llamamos la tecnica ganadora de la base de datos
        gemelo_ganador = next(c for c in top_3_gemelos if c.historial.tecnica.id == id_tecnica_ganadora)
        tecnica_ganadora = gemelo_ganador.historial.tecnica
        
        # Promedio de similitud de los gemelos
        similitud_promedio = sum(g.similitud for g in top_3_gemelos) / len(top_3_gemelos)
        
        return RecomendacionTecnica(
            tecnica=tecnica_ganadora,
            confianza=round(similitud_promedio * 100, 2),
            tasa_exito_historica = 0.0,
            casos_similares_usados=len(top_3_gemelos),
            razonamiento=f'La técnica "{tecnica_ganadora.nombre}" fue la más exitosa entre los casos similares encontrados, con una similitud promedio de {round(similitud_promedio * 100, 2)}% con el cliente actual.'
        )
            
# ==================================================
# ORQUESTADOS PRINCIPAL
# ==================================================

class GeneradorAnalisis:
    def __init__(self):
        self.scoring_engine = ScoringEngine()
        self.cbr_engine = CBREngine()
        
    def procesar_cliente(self, cliente: Cliente) -> AnalisisCompleto:
        
        perfil_riesgo = self.scoring_engine.calcular(cliente)
        tecnica_recomendada = self.cbr_engine.recomendar_estrategia(cliente)
        
        # Si el motor cbr no tiene historial devuelve una lista vacia
        lista_tecnicas = [tecnica_recomendada] if tecnica_recomendada else []
        
        ventas_activas = cliente.compras_realizadas.filter(estado_pago__in=['PENDIENTE', 'EN_MORA'])
        monto_mora = sum(venta.total_pagar for venta in ventas_activas if venta.estado_pago == 'EN_MORA')
        
        resumen = (
            f"El cliente {cliente.nombres} presenta un perfil de riesgo {perfil_riesgo.categoria_sugerida} con un score del {perfil_riesgo.score_porcentaje}%. "
            f"({perfil_riesgo.score_bruto * 100}%)"
        )
        
        if tecnica_recomendada:
            resumen += f" Se recomienda aplicar la técnica '{tecnica_recomendada.tecnica.nombre}' basada en casos similares del pasado con una confianza del {round(tecnica_recomendada.confianza * 100, 2)}%."
        else: 
            resumen += " No se encontraron casos similares para recomendar una técnica específica, se sugiere aplicar una estrategia estándar de cobranza."
        
        return AnalisisCompleto(
            cliente=cliente,
            perfil_riesgo=perfil_riesgo,
            tecnicas_recomendadas=lista_tecnicas,
            diferidos_recomendados=[],
            productos_recomendados=[],
            monto_total_mora=Decimal(monto_mora),
            resumen_ejecutivo=resumen
        )
        
        
# ======================================================
# FUNCION FANTASMA PARA LAS COMISIONES MAS ADELANTE
# ======================================================

def calcular_comision_vendedor(venta_editada) -> Decimal:
    # 5% de comisión estándar)
    porcentaje_comision = Decimal('0.05') 
    
    if venta_editada.total_pagar and venta_editada.colaborador:
        
        comision_final = venta_editada.total_pagar * porcentaje_comision
        venta_editada.comision_calculada = comision_final
        venta_editada.save()        
        return comision_final
        
    return Decimal('0.00')
