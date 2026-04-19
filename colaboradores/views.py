from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Producto, UsuarioVIP, Venta, ComisionCalculada, Vendedor, Producto
from django.contrib.auth.hashers import make_password, check_password
from django.contrib import messages

#LISTA DE LOS PRODUCTOS
@login_required(login_url='/login/') 
def panel_principal(request):
    lista_productos = Producto.objects.all()
    
    contexto = {
        'productos': lista_productos,
    }
    return render(request, 'panel.html', contexto)

#VISTAS DEL CRUD DE PRODUCTOS (OLLAS)
@login_required(login_url='/login/')
def crear_producto(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        precio = request.POST.get('precio')
        stock = request.POST.get('stock')
        
        Producto.objects.create(nombre=nombre, precio=precio, stock=stock)
    return redirect('panel')

@login_required(login_url='/login/')
def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        producto.delete()
    return redirect('panel')

@login_required(login_url='/login/')
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    
    if request.method == 'POST':
        producto.nombre = request.POST.get('nombre')
        producto.precio = request.POST.get('precio')
        producto.stock = request.POST.get('stock')
        producto.save() 
        return redirect('panel')
        
    return render(request, 'editarProducto.html', {'producto': producto})

#LOGIN PARA USUARIOS PERSONALIZADOS
def registro_vip(request):
    if request.method == 'POST':
        user_input = request.POST.get('username')
        pass_input = request.POST.get('password')
        clave_segura = make_password(pass_input) 
        
        UsuarioVIP.objects.create(username=user_input, password=clave_segura)
        return redirect('login_vip') 
        
    return render(request, 'registro_vip.html')

def login_vip(request):
    if request.method == 'POST':
        user_input = request.POST.get('username')
        pass_input = request.POST.get('password')
        
        try:
            usuario_encontrado = UsuarioVIP.objects.get(username=user_input)
            if check_password(pass_input, usuario_encontrado.password):
                request.session['vip_id'] = usuario_encontrado.id 
                request.session['vip_nombre'] = usuario_encontrado.username
                return redirect('zona_secreta')
            else:
                return render(request, 'login_vip.html', {'error': 'Contraseña incorrecta'})
                
        except UsuarioVIP.DoesNotExist:
            return render(request, 'login_vip.html', {'error': 'Ese usuario no existe'})
            
    return render(request, 'login_vip.html')

def zona_secreta(request):
    if 'vip_id' not in request.session:
        return redirect('login_vip') 
    nombre_vip = request.session.get('vip_nombre')
    return render(request, 'zona_secreta.html', {'nombre': nombre_vip})

def logout_vip(request):
    if 'vip_id' in request.session:
        del request.session['vip_id']
        del request.session['vip_nombre']
    return redirect('login_vip')

#MINICORE
@login_required(login_url='/login/')
def registrar_venta(request):
    if request.method == 'POST':
        vendedor_id = request.POST.get('vendedor')
        producto_id = request.POST.get('producto')
        cantidad = int(request.POST.get('cantidad'))
        
        vendedor = Vendedor.objects.get(id=vendedor_id)
        producto = Producto.objects.get(id=producto_id)
        
        monto_total = producto.precio * cantidad
        
        nueva_venta = Venta.objects.create(
            vendedor=vendedor,
            producto=producto,
            cantidad=cantidad,
            monto=monto_total
        )
        
        monto_comision = nueva_venta.calcular_comision()
        
        if monto_comision > 0:
            ComisionCalculada.objects.create(
                venta=nueva_venta,
                monto_comision=monto_comision
            )
            
        messages.success(request, f'Venta registrada con éxito. Comisión generada: ${monto_comision}')
        return redirect('registrar_venta') 

    else:
        vendedores = Vendedor.objects.all()
        productos = Producto.objects.all()
        contexto = {
            'vendedores': vendedores,
            'productos': productos
        }
        return render(request, 'registrar_venta.html', contexto)