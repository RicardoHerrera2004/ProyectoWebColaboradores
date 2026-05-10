from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from .models import (Producto, Venta, Vendedor, Cliente, CategoriaRiesgo, Diferido, TecnicaMejora, HistorialGestion)
from .forms import (ClienteForm, CategoriaRiesgoForm, DiferidoForm, TecnicaMejoraForm, HistorialGestionForm, VentaForm, CrearVendedorForm, EditarVendedorForm)

# ==========================================
# 1. AUTENTICACIÓN Y ENRUTAMIENTO PRINCIPAL
# ==========================================

def vista_login(request):
    if request.user.is_authenticated:
        return redirect('principal_panel')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)
            return redirect('principal_panel')
    else:
        form = AuthenticationForm()
    return render(request, 'login_usuario.html', {'form': form})

def vista_logout(request):
    logout(request)
    return redirect('login_usuario')

@login_required(login_url='login_usuario')
def principal_panel(request):
    if request.user.is_staff:
        contexto = {
            'total_clientes': Cliente.objects.count(),
            'ventas_mes': Venta.objects.count(),
            'morosidad_global': Cliente.objects.filter(categoria_riesgo__codigo='CRITICO').count()
        }
        return render(request, 'principal_panel.html', contexto)
    else:
        vendedor = get_object_or_404(Vendedor, user=request.user)
        ventas_en_mora = Venta.objects.filter(colaborador=vendedor, estado_pago='EN_MORA')
        contexto = {
            'mis_ventas': Venta.objects.filter(colaborador=vendedor).count(),
            'clientes_mora': ventas_en_mora.count(),
            'lista_ventas_mora': ventas_en_mora 
        }
        return render(request, 'panel_colaborador.html', contexto)

# ==========================================
# 2. MOTOR ANALÍTICO CBR (CORE)
# ==========================================

def calcular_scoring_riesgo(cliente):
    """
    Implementación de la ecuación Scoring (PDF 1.2.1):
    Nivel_Riesgo = (Dias_Mora_Historico / Total_Diferidos) * Factor_Severidad
    """
    total_diferidos = cliente.compras_realizadas.count()
    if total_diferidos == 0:
        return # No hay historial suficiente
    
    factor = cliente.categoria_riesgo.factor_severidad if cliente.categoria_riesgo else 1.0
    score = (cliente.incidencias_mora_total / total_diferidos) * factor

    if score > 0.8:
        cliente.categoria_riesgo = CategoriaRiesgo.objects.get(codigo='CRITICO')
    elif score > 0.4:
        cliente.categoria_riesgo = CategoriaRiesgo.objects.get(codigo='MEDIO')
    else:
        cliente.categoria_riesgo = CategoriaRiesgo.objects.get(codigo='ACEPTABLE')
    cliente.save()

# ==========================================
# 3. MÓDULO DE VENTAS Y GESTIÓN DE MORA
# ==========================================

@login_required
def historial_ventas(request):
    if request.user.is_staff:
        ventas = Venta.objects.all().order_by('-fecha')
    else:
        vendedor = get_object_or_404(Vendedor, user=request.user)
        ventas = Venta.objects.filter(colaborador=vendedor).order_by('-fecha')
    return render(request, 'historial_ventas.html', {'ventas': ventas})

@login_required
def registrar_venta(request):
    if request.method == 'POST':
        form = VentaForm(request.POST)
        if form.is_valid():
            venta = form.save()
            messages.success(request, f'Venta #{venta.id} autorizada según nivel de riesgo.')
            return redirect('principal_panel')
        else:
            messages.error(request, 'La venta no cumple con las políticas de riesgo crediticio.')
    else:
        form = VentaForm()
    return render(request, 'registrar_venta.html', {'form': form})

def cargar_diferidos(request):
    cliente_id = request.GET.get('cliente_id')
    diferidos = Diferido.objects.all()

    if cliente_id:
        try:
            cliente = Cliente.objects.get(id=cliente_id)
            riesgo = cliente.categoria_riesgo.codigo if cliente.categoria_riesgo else 'ACEPTABLE'
            
            if riesgo == 'CRITICO':
                diferidos = diferidos.filter(meses_plazo__lte=3)
            elif riesgo == 'MEDIO':
                diferidos = diferidos.filter(requiere_entrada=True)
        except Cliente.DoesNotExist:
            pass

    data = list(diferidos.values('id', 'meses_plazo', 'porcentaje_interes'))
    return JsonResponse(data, safe=False)

@login_required
def registrar_gestion_mora(request):
    if request.method == 'POST':
        form = HistorialGestionForm(request.POST)
        if form.is_valid():
            gestion = form.save()
            calcular_scoring_riesgo(gestion.cliente)
            messages.success(request, 'Resultado de gestión guardado. El Motor CBR ha actualizado el perfil.')
            return redirect('principal_panel')
    else:
        form = HistorialGestionForm()
    return render(request, 'registrar_gestion.html', {'form': form})

# ==========================================
# 4. CRUD: CLIENTES
# ==========================================

@login_required
def lista_clientes(request):
    clientes = Cliente.objects.select_related('categoria_riesgo').all()
    return render(request, 'lista_clientes.html', {'clientes': clientes})

@login_required
def registrar_cliente_admin(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save()
            messages.success(request, f'Cliente {cliente.nombres} registrado con validación exitosa.')
            return redirect('principal_panel')
    else:
        form = ClienteForm()
    return render(request, 'registrar_cliente.html', {'form': form})

@login_required
def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Datos del cliente actualizados exitosamente.')
            return redirect('lista_clientes')
    else:
        form = ClienteForm(instance=cliente)
    return render(request, 'formulario_generico.html', {'form': form, 'titulo': f'Editar Cliente: {cliente.nombres}'})

@login_required
def eliminar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        if request.user.is_staff:
            cliente.delete()
            messages.success(request, 'Cliente eliminado del sistema.')
        else:
            messages.error(request, 'No tienes permisos para eliminar clientes.')
    return redirect('lista_clientes')

@login_required
def ver_historial_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    historial = HistorialGestion.objects.filter(cliente=cliente).order_by('-fecha_aplicacion')
    contexto = {
        'cliente': cliente,
        'historial': historial,
        'titulo': f'Historial de Gestión: {cliente.nombres}'
    }
    return render(request, 'ver_historial_cliente.html', contexto)

# ==========================================
# 5. CRUD: VENDEDORES / COLABORADORES
# ==========================================

@login_required(login_url='login_usuario')
def lista_vendedores(request):
    if not request.user.is_staff:
        messages.error(request, "Acceso restringido a Recursos Humanos.")
        return redirect('panel_principal')
    vendedores = Vendedor.objects.select_related('user').all()
    return render(request, 'lista_vendedores.html', {'vendedores': vendedores})

@login_required(login_url='login_usuario')
def crear_vendedor(request):
    if not request.user.is_staff:
        return redirect('panel_principal')
    if request.method == 'POST':
        form = CrearVendedorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Colaborador creado. Ya puede iniciar sesión en el sistema.')
            return redirect('lista_vendedores')
    else:
        form = CrearVendedorForm()
    return render(request, 'formulario_generico.html', {'form': form, 'titulo': 'Registrar Nuevo Colaborador'})

@login_required(login_url='login_usuario')
def editar_vendedor(request, pk):
    if not request.user.is_staff:
        return redirect('panel_principal')
    vendedor = get_object_or_404(Vendedor, pk=pk)
    if request.method == 'POST':
        form = EditarVendedorForm(request.POST, instance=vendedor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil del colaborador actualizado correctamente.')
            return redirect('lista_vendedores')
    else:
        form = EditarVendedorForm(instance=vendedor)
    return render(request, 'formulario_generico.html', {'form': form, 'titulo': f'Editar Colaborador: {vendedor.nombre_completo}'})

@login_required(login_url='login_usuario')
def eliminar_vendedor(request, pk):
    vendedor = get_object_or_404(Vendedor, pk=pk)
    if request.method == 'POST' and request.user.is_staff:
        user = vendedor.user
        user.delete() 
        messages.success(request, 'Colaborador dado de baja del sistema.')
    return redirect('lista_vendedores')

# ==========================================
# 6. CRUD: PRODUCTOS
# ==========================================

@login_required
def panel_productos(request):
    productos = Producto.objects.all()
    return render(request, 'principal_panel.html', {'productos': productos, 'seccion': 'productos'})

@login_required
def crear_producto(request):
    if request.method == 'POST':
        Producto.objects.create(
            codigo_sku=request.POST.get('sku'),
            nombre=request.POST.get('nombre'),
            precio=request.POST.get('precio'),
            stock=request.POST.get('stock'),
            tipo=request.POST.get('tipo', 'OLLA')
        )
        messages.success(request, 'Producto añadido al catálogo.')
    return redirect('panel_productos')

@login_required
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        producto.nombre = request.POST.get('nombre')
        producto.precio = request.POST.get('precio')
        producto.stock = request.POST.get('stock')
        producto.save()
        return redirect('panel_productos')
    return render(request, 'editar_producto.html', {'producto': producto})

@login_required
def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        producto.delete()
    return redirect('panel_productos')

# ==========================================
# 7. CRUD: CATEGORÍAS DE RIESGO
# ==========================================

@login_required
def lista_categorias(request):
    if not request.user.is_staff:
        messages.error(request, "Acceso restringido a administradores.")
        return redirect('principal_panel')
    categorias = CategoriaRiesgo.objects.all()
    return render(request, 'lista_categorias.html', {'categorias': categorias})

@login_required
def crear_categoria(request):
    if not request.user.is_staff:
        return redirect('principal_panel')
    if request.method == 'POST':
        form = CategoriaRiesgoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría de Riesgo creada.')
            return redirect('lista_categorias')
    else:
        form = CategoriaRiesgoForm()
    return render(request, 'formulario_generico.html', {'form': form, 'titulo': 'Nueva Categoría de Riesgo'})

@login_required
def editar_categoria(request, pk):
    if not request.user.is_staff:
        return redirect('principal_panel')
    categoria = get_object_or_404(CategoriaRiesgo, pk=pk)
    if request.method == 'POST':
        form = CategoriaRiesgoForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Categoría de Riesgo actualizada.')
            return redirect('lista_categorias')
    else:
        form = CategoriaRiesgoForm(instance=categoria)
    return render(request, 'formulario_generico.html', {'form': form, 'titulo': f'Editar Categoría: {categoria.codigo}'})

@login_required
def eliminar_categoria(request, pk):
    categoria = get_object_or_404(CategoriaRiesgo, pk=pk)
    if request.method == 'POST' and request.user.is_staff:
        categoria.delete()
        messages.success(request, 'Categoría eliminada.')
    return redirect('lista_categorias')

# ==========================================
# 8. CRUD: PLANES DIFERIDOS
# ==========================================

@login_required
def lista_diferidos(request):
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado. Se requieren permisos administrativos.")
        return redirect('principal_panel')
    diferidos = Diferido.objects.all().order_by('meses_plazo')
    return render(request, 'lista_diferidos.html', {'diferidos': diferidos})

@login_required
def crear_diferido(request):
    if not request.user.is_staff:
        return redirect('principal_panel')
    if request.method == 'POST':
        form = DiferidoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Plan diferido creado.')
            return redirect('lista_diferidos')
    else:
        form = DiferidoForm()
    return render(request, 'formulario_generico.html', {'form': form, 'titulo': 'Nuevo Plan Diferido'})

@login_required
def editar_diferido(request, pk):
    if not request.user.is_staff:
        return redirect('principal_panel')
    diferido = get_object_or_404(Diferido, pk=pk)
    if request.method == 'POST':
        form = DiferidoForm(request.POST, instance=diferido)
        if form.is_valid():
            form.save()
            messages.success(request, 'Plan ddeleteiferido actualizado.')
            return redirect('lista_diferidos')
    else:
        form = DiferidoForm(instance=diferido)
    return render(request, 'formulario_generico.html', {'form': form, 'titulo': f'Editar Diferido: {diferido.meses_plazo} meses'})

@login_required
def eliminar_diferido(request, pk):
    diferido = get_object_or_404(Diferido, pk=pk)
    if request.method == 'POST' and request.user.is_staff:
        diferido.delete()
        messages.success(request, 'Plan diferido eliminado.')
    return redirect('lista_diferidos')

# ==========================================
# 9. CRUD: TÉCNICAS CBR
# ==========================================

@login_required
def lista_tecnicas(request):
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado. Solo los administradores pueden gestionar el repositorio CBR.")
        return redirect('principal_panel')
    tecnicas = TecnicaMejora.objects.all().order_by('nombre')
    return render(request, 'lista_tecnicas.html', {'tecnicas': tecnicas})

@login_required
def crear_tecnica(request):
    if request.method == 'POST':
        form = TecnicaMejoraForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Técnica guardada correctamente.')
            return redirect('lista_tecnicas')
    else:
        form = TecnicaMejoraForm()
    return render(request, 'formulario_generico.html', {'form': form, 'titulo': 'Crear Nueva Técnica CBR'})

@login_required
def editar_tecnica(request, pk):
    tecnica = get_object_or_404(TecnicaMejora, pk=pk)
    if request.method == 'POST':
        form = TecnicaMejoraForm(request.POST, instance=tecnica)
        if form.is_valid():
            form.save()
            messages.success(request, 'Técnica actualizada.')
            return redirect('lista_tecnicas')
    else:
        form = TecnicaMejoraForm(instance=tecnica)
    return render(request, 'formulario_generico.html', {'form': form, 'titulo': f'Editar Técnica: {tecnica.nombre}'})

@login_required
def eliminar_tecnica(request, pk):
    tecnica = get_object_or_404(TecnicaMejora, pk=pk)
    if request.method == 'POST' and request.user.is_staff:
        tecnica.delete()
        messages.success(request, 'Técnica CBR eliminada exitosamente.')
    return redirect('lista_tecnicas')