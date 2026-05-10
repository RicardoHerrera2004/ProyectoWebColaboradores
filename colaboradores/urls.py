from django.urls import path
from . import views

urlpatterns = [
    # ---------------------------------------------------------
    # 1. ACCESO Y SEGURIDAD
    # ---------------------------------------------------------
    path('login/', views.vista_login, name='login_usuario'),
    path('logout/', views.vista_logout, name='vista_logout'),
    path('', views.principal_panel, name='principal_panel'),

    # ---------------------------------------------------------
    # 2. PARAMETRIZACIÓN ESTRATÉGICA (Solo Administradores)
    # ---------------------------------------------------------
    # CRUD Categorías de Riesgo
    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('categorias/crear/', views.crear_categoria, name='crear_categoria'),
    path('categorias/editar/<int:pk>/', views.editar_categoria, name='editar_categoria'),
    path('categorias/eliminar/<int:pk>/', views.eliminar_categoria, name='eliminar_categoria'),

    # CRUD Planes Diferidos
    path('diferidos/', views.lista_diferidos, name='lista_diferidos'),
    path('diferidos/crear/', views.crear_diferido, name='crear_diferido'),
    path('diferidos/editar/<int:pk>/', views.editar_diferido, name='editar_diferido'),
    path('diferidos/eliminar/<int:pk>/', views.eliminar_diferido, name='eliminar_diferido'),

    # CRUD Técnicas de Mejora (Repositorio CBR)
    path('tecnicas/', views.lista_tecnicas, name='lista_tecnicas'),
    path('tecnicas/crear/', views.crear_tecnica, name='crear_tecnica'),
    path('tecnicas/editar/<int:pk>/', views.editar_tecnica, name='editar_tecnica'),
    path('tecnicas/eliminar/<int:pk>/', views.eliminar_tecnica, name='eliminar_tecnica'),

    # ---------------------------------------------------------
    # 3. GESTIÓN DE CARTERA Y CORE (Colaboradores / Vendedores)
    # ---------------------------------------------------------
    # CRUD Clientes
    path('clientes/', views.lista_clientes, name='lista_clientes'),
    path('clientes/registrar/', views.registrar_cliente_admin, name='registrar_cliente_admin'),
    path('clientes/editar/<int:pk>/', views.editar_cliente, name='editar_cliente'),
    path('clientes/eliminar/<int:pk>/', views.eliminar_cliente, name='eliminar_cliente'),

    # Registro de Gestiones de Mora (Alimentación del Motor)
    path('gestiones/registrar/', views.registrar_gestion_mora, name='registrar_gestion_mora'),
    path('gestiones/historial/<int:cliente_id>/', views.ver_historial_cliente, name='ver_historial_cliente'),

    # ---------------------------------------------------------
    # 4. MÓDULO DE VENTAS Y PRODUCTOS
    # ---------------------------------------------------------
    path('productos/', views.panel_productos, name='panel_productos'),
    path('productos/crear/', views.crear_producto, name='crear_producto'),
    path('productos/editar/<int:producto_id>/', views.editar_producto, name='editar_producto'),
    path('productos/eliminar/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),

    path('ventas/registrar/', views.registrar_venta, name='registrar_venta'),
    path('ventas/historial/', views.historial_ventas, name='historial_ventas'),

    path('colaboradores/', views.lista_vendedores, name='lista_vendedores'),
    path('colaboradores/crear/', views.crear_vendedor, name='crear_vendedor'),
    path('colaboradores/editar/<int:pk>/', views.editar_vendedor, name='editar_vendedor'),
    path('colaboradores/eliminar/<int:pk>/', views.eliminar_vendedor, name='eliminar_vendedor'),

    # ---------------------------------------------------------
    # APIs Y ENDPOINTS DINÁMICOS (Requisitos de la Rúbrica)
    # ---------------------------------------------------------
    # Endpoint para el dropdown dependiente según el Scoring de Riesgo
    path('api/diferidos-permitidos/', views.cargar_diferidos, name='ajax_cargar_diferidos'),
]