from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from django.db.models import Count
from django.core.exceptions import ObjectDoesNotExist
from .models import Cliente, Venta, DetalleVenta, Diferido, Producto, TecnicaMejora, HistorialGestion, CategoriaRiesgo, PerfilSocioeconomico
import math
from abc import ABC, abstractmethod

# =============================================================================
# 1. ESTRUCTURAS DE DATOS (DTOs)
# =============================================================================

@dataclass
class PerfilRiesgo:
    score_bruto: float
    score_porcentaje: float                        
    categoria_sugerida: str
    factores: dict
    confianza: float

@dataclass
class CasoSimilar:
    historial: HistorialGestion
    similitud: float
    factores_coicidencias: list

@dataclass
class RecomendacionTecnica:
    tecnica: TecnicaMejora
    confianza: float
    tasa_exito_historica: float
    casos_similares_usados: int
    razonamiento: str
    
@dataclass
class RecomendacionDiferido:
    diferido: Diferido
    cuota_estimada: Decimal
    porcentaje_sobre_capacidad: float
    viable: bool
    nivel_riesgo: str
    razon: str
    
@dataclass
class RecomendacionProducto:
    producto: Producto
    puntuacion: float
    razon: str
    
@dataclass
class AnalisisCompleto:
    cliente: Cliente
    perfil_riesgo: PerfilRiesgo
    tecnicas_recomendadas: list
    diferidos_recomendados: list
    productos_recomendados: list
    monto_total_mora: Decimal
    resumen_ejecutivo: str

# =============================================================================
# 2. PATRÓN STRATEGY + OCP (Abierto a extensión, Cerrado a modificación)
# =============================================================================

class EstrategiaSimilitud(ABC):
    @abstractmethod
    def calcular(self, vec1: list, vec2: list) -> float:
        pass

class SimilitudEuclidiana(EstrategiaSimilitud):
    def calcular(self, vec1: list, vec2: list) -> float:
        if len(vec1) != len(vec2):
            return 0.0
        
        # Teorema de pitagoras
        suma_cuadrados = sum((a - b) ** 2 for a, b in zip(vec1, vec2))
        distancia = math.sqrt(suma_cuadrados)
        
        # Normalización
        distancia_maxima = math.sqrt(len(vec1))
        distancia_normalizada = distancia / distancia_maxima if distancia_maxima > 0 else 0
        similitud = 1.0 - distancia_normalizada 
        
        return round(similitud, 4)


# =============================================================================
# 3. MÓDULOS DE NEGOCIO AISLADOS (Principio SRP - Responsabilidad Única)
# =============================================================================

class CalculadoraComisiones:
    """Responsabilidad: Calcular remuneraciones de ventas. (Antes era una función suelta)"""
    def calcular_por_diferidos(self, venta: Venta) -> Decimal:
        calculo_porcentaje_diferido = venta.diferido.porcentaje_interes if venta.diferido else 0
        comision = Decimal(calculo_porcentaje_diferido) * Decimal(venta.total_pagar) 
        return comision.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

class ScoringEngine:
    """Responsabilidad: Evaluar riesgo crediticio en base a mora."""
    PESOS = {
        'tasa_mora': 0.35,           
        'recencia_mora': 0.3,        
        'carga_financiera': 0.2,     
        'concentracion': 0.15        
    }
    UMBRAL = {
        'CRITICO': 0.65,             
        'MEDIO': 0.35,               
    }
    
    def calcular(self, cliente: Cliente) -> PerfilRiesgo:
        ventas = list(cliente.compras_realizadas.select_related('diferido').all())
        total = len(ventas)
        
        if total == 0:
            return PerfilRiesgo(score_bruto=0.0, score_porcentaje=0.0, categoria_sugerida='ACEPTABLE', factores={}, confianza=0.0)
        
        en_mora = [v for v in ventas if v.estado_pago == 'EN_MORA']
            
        factores = {
            'tasa_mora': self._tasa_mora(en_mora, total),                  
            'recencia_mora': self._recencia_mora(ventas, total),            
            'carga_financiera': self._carga_financiera(cliente, ventas),    
            'concentracion': self._concentracion_mora(en_mora)              
        }
        
        score_base = sum(factores[clave] * self.PESOS[clave] for clave in self.PESOS)
        sev = cliente.categoria_riesgo.factor_severidad if cliente.categoria_riesgo else 1.0
        score_ajustado = min(score_base * sev, 1.0)
        
        categoria = 'ACEPTABLE'
        if score_ajustado >= self.UMBRAL['CRITICO']: categoria = 'CRITICO'
        elif score_ajustado >= self.UMBRAL['MEDIO']: categoria = 'MEDIO'

        confianza = round(min(total / 8.0, 1.0), 4)
        
        return PerfilRiesgo(
            score_bruto=round(score_base, 4),
            score_porcentaje=round(score_ajustado * 100, 2),
            categoria_sugerida=categoria, 
            factores={k.replace('_', ' ').title(): round(v * 100, 4) for k, v in factores.items()},
            confianza=confianza 
        )

    def _tasa_mora(self, en_mora: list, total: int) -> float:
        return len(en_mora) / total

    def _recencia_mora(self, ventas: list, total: int) -> float:
        recientes = sorted(ventas, key=lambda v: v.fecha_emision, reverse=True)[:5]  
        mora_reciente = sum(1 for v in recientes if v.estado_pago == 'EN_MORA')
        return mora_reciente / min(5, total)  

    def _carga_financiera(self, cliente: Cliente, ventas: list) -> float:   
        try:
            ingresos = float(cliente.perfil_socioeconomico.ingreso_mensual or 0)
            if ingresos <= 0: return 0.5
            gastos = float(cliente.perfil_socioeconomico.gastos_fijos_estimados or 0)
            activas = [venta for venta in ventas if venta.estado_pago in ['PENDIENTE', 'EN_MORA']]
            total_cuotas = sum(float(venta.valor_mensualidad) for venta in activas)
            carga_total_real = gastos + total_cuotas
            return min(carga_total_real / ingresos, 1.0)
        except (AttributeError, PerfilSocioeconomico.DoesNotExist):
            return 0.5 
        
    def _concentracion_mora(self, en_mora: list) -> float:
        if not en_mora: return 0.0
        grupos_deuda = {}
        for venta in en_mora:
            clave = (venta.diferido.id if venta.diferido else 'contado')
            grupos_deuda[clave] = grupos_deuda.get(clave, 0) + 1
            
        total_cuotas_impagas = len(en_mora)
        cantidad_planes_distintos = len(grupos_deuda)
        indice_concentracion = sum((count / total_cuotas_impagas) ** 2 for count in grupos_deuda.values())
        indice_concentracion_minimo = 1 / cantidad_planes_distintos if cantidad_planes_distintos > 0 else 1.0
        if indice_concentracion_minimo >= 1.0: return 0.0
        nota_final_normalizada = (indice_concentracion - indice_concentracion_minimo) / (1 - indice_concentracion_minimo)
        return round(nota_final_normalizada, 4)
    
class CBREngine:
    """Responsabilidad: Comparar vectores para buscar similitudes históricas."""
    
    # Inyección de dependencias (Strategy)
    def __init__(self, estrategia: EstrategiaSimilitud):
        self.estrategia = estrategia
        
    def _vectorizar_perfil(self, cliente: Cliente) -> list:
        try: 
            perfil = cliente.perfil_socioeconomico
        except AttributeError:
            return [0.5, 0.5, 0.5, 0.5]
    
        ingreso_norm = min(float(perfil.ingreso_mensual or 0) / 3000.0, 1.0)
        cargas_norm = min(perfil.numero_hijos / 5.0, 1.0)
        
        mapa_estudios = {'PRIMARIA': 0.25, 'SECUNDARIA': 0.5, 'TERCER_NIVEL': 0.75, 'CUARTO_NIVEL': 1.0}
        estudios_norm = mapa_estudios.get(perfil.nivel_estudio, 0.5)
    
        mapa_civil = {'SOLTERO': 0.0, 'DIVORCIADO': 0.4, 'CASADO': 0.7, 'UNION_LIBRE': 0.8}
        civil_norm = mapa_civil.get(getattr(perfil, 'estado_civil', ''), 0.5)
    
        return [ingreso_norm, cargas_norm, estudios_norm, civil_norm]

    def recomendar_estrategia(self, cliente_actual: Cliente) -> RecomendacionTecnica:
        vector_actual = self._vectorizar_perfil(cliente_actual)
        casos_existosos = HistorialGestion.objects.filter(fue_exitosa=True).select_related('cliente', 'tecnica').all()
        casos_evaluados = []
        
        for caso in casos_existosos:
            if caso.cliente.id == cliente_actual.id:
                continue
            
            vector_historico = self._vectorizar_perfil(caso.cliente)
            # El motor delega la matemática a la estrategia externa
            similitud = self.estrategia.calcular(vector_actual, vector_historico)
            
            casos_evaluados.append(CasoSimilar(historial=caso, similitud=similitud, factores_coicidencias=[]))
            
        if not casos_evaluados:
            return None
        
        top_3_gemelos = sorted(casos_evaluados, key=lambda c: c.similitud, reverse=True)[:3]
        
        votos_tecnicas = {}
        for gemelo in top_3_gemelos:
            id_tecnica = gemelo.historial.tecnica.id
            votos_tecnicas[id_tecnica] = votos_tecnicas.get(id_tecnica, 0.0) + gemelo.similitud
            
        id_tecnica_ganadora = max(votos_tecnicas, key=votos_tecnicas.get)
        gemelo_ganador = next(c for c in top_3_gemelos if c.historial.tecnica.id == id_tecnica_ganadora)
        tecnica_ganadora = gemelo_ganador.historial.tecnica
        
        similitud_promedio = sum(g.similitud for g in top_3_gemelos) / len(top_3_gemelos)
        
        return RecomendacionTecnica(
            tecnica=tecnica_ganadora,
            confianza=round(similitud_promedio * 100, 2),
            tasa_exito_historica = 0.0,
            casos_similares_usados=len(top_3_gemelos),
            razonamiento=f'La técnica "{tecnica_ganadora.nombre}" fue la más exitosa entre los casos similares encontrados, con una similitud promedio de {round(similitud_promedio * 100, 2)}%.'
        )

# =============================================================================
# 4. PATRÓN FACADE (Orquestador principal para views.py)
# =============================================================================

class SistemaCoreFacade:
    """Proporciona una interfaz unificada para acceder a los motores complejos."""
    def __init__(self):
        # Ensamblaje de subsistemas (Aquí inyectamos la matemática euclidiana)
        self.scoring_engine = ScoringEngine()
        self.cbr_engine = CBREngine(estrategia=SimilitudEuclidiana())
        self.calculadora_comisiones = CalculadoraComisiones()
        
    def procesar_cliente(self, cliente: Cliente) -> AnalisisCompleto:
        """Llamada principal para expedientes de clientes."""
        perfil_riesgo = self.scoring_engine.calcular(cliente)
        tecnica_recomendada = self.cbr_engine.recomendar_estrategia(cliente)
        lista_tecnicas = [tecnica_recomendada] if tecnica_recomendada else []
        
        ventas_activas = cliente.compras_realizadas.filter(estado_pago__in=['PENDIENTE', 'EN_MORA'])
        monto_mora = sum(venta.total_pagar for venta in ventas_activas if venta.estado_pago == 'EN_MORA')
        
        resumen = (f"El cliente {cliente.nombres} presenta un perfil de riesgo {perfil_riesgo.categoria_sugerida} "
                   f"con un score del {perfil_riesgo.score_porcentaje}%. ({perfil_riesgo.score_bruto * 100}%)")
        
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

    def obtener_comision_venta(self, venta: Venta) -> Decimal:
        """Llamada simplificada para que tu vista obtenga la comisión."""
        return self.calculadora_comisiones.calcular_por_diferidos(venta)