from django.urls import path
from . import views

urlpatterns = [
    #Url principal
    path('', views.panel_principal, name='panel'),
    
    #Urls del CRUD de productos
    path('crear-producto/', views.crear_producto, name='crear_producto'),
    path('eliminar-producto/<int:producto_id>/', views.eliminar_producto, name='eliminar_producto'),
    path('editar-producto/<int:producto_id>/', views.editar_producto, name='editar_producto'),
    
    #Urls del Login Personalizado
    path('vip/registro/', views.registro_vip, name='registro_vip'),
    path('vip/login/', views.login_vip, name='login_vip'),
    path('vip/zona-secreta/', views.zona_secreta, name='zona_secreta'),
    path('vip/logout/', views.logout_vip, name='logout_vip'),
]

