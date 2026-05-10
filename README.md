# Sistema Analítico CBR - Cookware Corp
# Gestión de Riesgo Crediticio y Recuperación de Cartera (Django Full-Stack)

![Estado](https://img.shields.io/badge/Estado-Desplegado_en_Producci%C3%B3n-success)
![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python)
![Django](https://img.shields.io/badge/Django-MVT-092E20?logo=django)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Render-336791?logo=postgresql)
![JavaScript](https://img.shields.io/badge/JavaScript-AJAX/jQuery-F7DF1E?logo=javascript)
![CSS3](https://img.shields.io/badge/CSS3-BEM_Architecture-1572B6?logo=css3)

## Descripción del Proyecto
Este proyecto es una aplicación web full-stack desarrollada bajo la arquitectura **Modelo-Vista-Template (MVT)** de Django. Funciona como un ecosistema corporativo para una empresa de utensilios de cocina, enfocado en el análisis de riesgo crediticio de los clientes y la gestión de cobranza. 

El núcleo del sistema es un **Motor de Razonamiento Basado en Casos (CBR)** que evalúa el historial de mora de los clientes para asignar categorías de riesgo dinámicas y restringir operaciones financieras en tiempo real.

## Enlace a Producción
El sistema se encuentra desplegado y funcional en la nube a través de Render:
**[Visitar la Intranet Corporativa](https://proyectowebcolaboradores.onrender.com)**

---

## Funcionalidades y Logros de Ingeniería

### 1. Motor Analítico de Riesgo (CBR)
* **Algoritmo de Scoring:** Cálculo matemático en el backend que clasifica a los clientes en categorías (Aceptable, Medio, Crítico) basándose en su historial de pagos y severidad de mora.
* **Ciclo de Aprendizaje:** Registro de intervenciones de cobranza donde el sistema recalcula el riesgo automáticamente tras evaluar el éxito o fracaso de una técnica aplicada.

### 2. Prevención de Riesgo en Tiempo Real (AJAX)
* **API Interna:** Creación de endpoints (`JsonResponse`) consumidos asíncronamente vía JavaScript.
* **Filtrado Dinámico (DOM):** Al momento de registrar una venta, el sistema consulta el riesgo del cliente sin recargar la página y bloquea opciones de financiamiento a largo plazo para perfiles críticos, mitigando el error humano.

### 3. Seguridad y Control de Acceso (RBAC)
* Implementación estricta del decorador `@login_required` y validación de roles (`is_staff`).
* **Panel de Administrador:** Acceso exclusivo a la configuración paramétrica (Diferidos, Técnicas CBR, Categorías) y gestión de nómina.
* **Panel de Colaborador:** Interfaz operativa enfocada en las métricas personales de ventas y gestión de clientes asignados en mora.

### 4. Arquitectura Frontend y UX/UI
* **Plantillas Genéricas DRY:** Uso avanzado de la herencia de Django (`{% extends %}`, `{% block %}`) para renderizar formularios CRUD múltiples desde un único archivo HTML.
* **Diseño CSS Global y Metodología BEM:** Arquitectura de estilos escalable, uso de *Flexbox* y *CSS Grid* para un diseño 100% responsivo y adaptado al entorno corporativo.
* **WhiteNoise:** Configuración optimizada para servir archivos estáticos eficientemente en producción.

---

## Instalación y Configuración Local
Si deseas probar o auditar el código de este proyecto en tu entorno local, sigue estos pasos:

1. **Clona el repositorio:**
   ```bash
   git clone [https://github.com/tu-usuario/tu-repositorio.git](https://github.com/tu-usuario/tu-repositorio.git)
   ```

2. **Crea y activa el entorno virtual:**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate

   # Mac/Linux:
   source venv/bin/activate

3. **Instala las dependencias exactas:**
   ```bash
   pip install -r requirements.txt

4. **Ejecuta las migraciones del sistema:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate

5. **Crea un superusuario (Administrador):**
   ```bash
   python manage.py createsuperuser

6. **Inicia el servidor de desarrollo:**
   ```bash
   python manage.py runserver

Navega a http://127.0.0.1:8000/ e inicia sesión con las credenciales creadas.

### Autor
Ricardo Herrera Estudiante de Ingeniería de Software - Universidad de las Américas (UDLA)
