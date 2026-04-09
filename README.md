# ProyectoWebColaboradores
# Intranet Corporativa & Portal VIP (Django Full-Stack)

![Estado](https://img.shields.io/badge/Estado-Completado-success)
![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python)
![Django](https://img.shields.io/badge/Django-MVT-092E20?logo=django)
![CSS3](https://img.shields.io/badge/CSS3-BEM_Architecture-1572B6?logo=css3)
![JavaScript](https://img.shields.io/badge/JavaScript-Fetch_API-F7DF1E?logo=javascript)

## Descripción del Proyecto
Este proyecto es una aplicación web full-stack desarrollada bajo la arquitectura **Modelo-Vista-Template (MVT)** de Django. Funciona como una intranet corporativa para la gestión de un catálogo de productos (ollas), destacando por la implementación de **dos sistemas de autenticación completamente independientes** coexistiendo en la misma aplicación, junto con integración de peticiones asíncronas para consumo de datos.

## Funcionalidades y Logros de Ingeniería

### 1. Gestión de Catálogo (CRUD)
* **Create, Read, Update, Delete:** Operaciones completas a la base de datos protegidas por vistas seguras.

### 2. Autenticación Dual 
* **Sistema Principal:** Autenticación nativa de Django con enrutamiento protegido (`@login_required`).
* **Portal VIP (Custom Auth):** Sistema paralelo construido **desde cero** para comprender el ciclo de vida HTTP. 
  * Algoritmo de encriptado de contraseñas (`make_password`, `check_password`).
  * Gestión manual de *cookies* y variables de sesión (`request.session`).
  * Vistas y rutas blindadas manualmente contra intrusos.

### 3. Arquitectura Frontend 
* **HTML5 Semántico:** Estructuración estricta usando `<main>`, `<section>`, `<header>`, `<footer>` y `<ul>` para garantizar accesibilidad y lectura por *Screen Readers*.
* **Diseño CSS Global y Metodología BEM:** * Normalización de etiquetas nativas (`inputs`, `buttons`).
  * Implementación del patrón *Block Element Modifier* (ej. `.btn--vip`) para un código escalable y libre de estilos en línea.
  * Uso intensivo de *Flexbox* y *CSS Grid* para un diseño 100% responsivo.

## 4. Instalación y Configuración Local
Si deseas probar este proyecto en tu entorno local, sigue estos pasos:

1. **Clona el repositorio:**
   ```bash
   git clone [https://github.com/tu-usuario/tu-repositorio.git](https://github.com/tu-usuario/tu-repositorio.git)
    ```

2. **Crea y activa el entorno virtual**
 ```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
 ```
 
3. **Instala las dependencias**
 ```bash
pip install django
 ```

4. **Ejectua las migraciones**
```bash
python manage.py makemigrations
python manage.py migrate
 ```

5. **Inicia el servidor**
```bash
python manage.py runserver
 ```
Navega a http://127.0.0.1:8000/ para ver la aplicación.

## 5. Autor
Ricardo Herrera - Estudiante de Ingeniería de Software
