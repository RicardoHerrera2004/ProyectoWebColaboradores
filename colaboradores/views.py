from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum
from .models import (Producto, Venta, Vendedor, Cliente, CategoriaRiesgo, Diferido, TecnicaMejora, HistorialGestion)
from .services import calcular_scoring_riesgo, calcular_comision_vendedor, motor_cbr_recomendar_tecnica
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
            'morosidad_global': Cliente.objects.filter(categoria_riesgo__codigo='CRITICO').count(),
            'productos': Producto.objects.all()
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
# 3. MÓDULO DE VENTAS Y GESTIÓN DE MORA
# ==========================================

@login_required
def historial_ventas(request):
    if request.user.is_staff:
        ventas = Venta.objects.all().order_by('-fecha_emision')
    else:
        vendedor = get_object_or_404(Vendedor, user=request.user)
        ventas = Venta.objects.filter(colaborador=vendedor).order_by('-fecha_emision')
        
    # 1. Ejecutamos la agregación pura
    datos_agregados = ventas.aggregate(suma_total=Sum('comision_ganada'))

    # 2. Extraemos el valor usando la clave personalizada 'suma_total'
    monto_crudo = datos_agregados.get('suma_total')

    # 3. Si es None (nulo), lo forzamos a ser 0.00
    total_comisiones = monto_crudo if monto_crudo is not None else 0.00
    
    contexto = {
        'ventas': ventas,
        'total_comisiones': round(total_comisiones, 2)
    }
    
    return render(request, 'historial_ventas.html', contexto)

@login_required
def registrar_venta(request):
    if request.method == 'POST':
        form = VentaForm(request.POST)
        if form.is_valid():
            # 1. commit=False: Construye el objeto Venta pero pausa el guardado en la BD
            nueva_venta = form.save(commit=False)
            
            vendedor_perfil = Vendedor.objects.filter(user=request.user).first()
            
            # 2. Asignamos al colaborador automáticamente según quién esté logueado 
            if vendedor_perfil:
                nueva_venta.colaborador = vendedor_perfil
            elif request.user.is_staff:
                # Si es administrador y no tiene perfil de vendedor, buscamos el primer vendedor
                # del sistema como respaldo, o puedes manejarlo según tu lógica de negocio.
                primer_vendedor = Vendedor.objects.first()
                if not primer_vendedor:
                    messages.error(request, 'Error crítico: No existen vendedores registrados en el sistema para asociar la venta.')
                    return redirect('principal_panel')
                nueva_venta.colaborador = primer_vendedor
            else:
                messages.error(request, 'Tu usuario no tiene un perfil de vendedor asignado.')
                return redirect('principal_panel')
            
            # 3. Llamamos al servicio financiero
            comision = calcular_comision_vendedor(nueva_venta)
            
            # 4. Inyectamos la comisión calculada en el campo 
            nueva_venta.comision_ganada = comision
            
            # 5. Si el formulario incluye una fecha manual (retroactiva) y el usuario es admin, la asignamos
            fecha_retroactiva = form.cleaned_data.get('fecha_manual')
            if fecha_retroactiva and request.user.is_staff:
                nueva_venta.fecha_emision = fecha_retroactiva
            
            # 6. Hacemos el INSERT en PostgreSQL/SQLite
            nueva_venta.save()
            
            # 7. Feedback claro al usuario
            messages.success(request, f'Venta registrada con éxito. Comisión generada: ${comision}')
            return redirect('historial_ventas')
        else:
            messages.error(request, 'La venta no cumple con las políticas de riesgo crediticio.')
    else:
        form = VentaForm()
    return render(request, 'registrar_venta.html', {'form': form})

@login_required
def editar_venta(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    
    if request.method == 'POST':
        form = VentaForm(request.POST, instance=venta)
        if form.is_valid():
            # 1. Guardamos primero los datos generales de la venta
            venta_editada = form.save(commit=False)
            comision = calcular_comision_vendedor(venta_editada)
            venta_editada.comision_ganada = comision
            venta_editada.save() 
            
            # 2. ⚡ TRUCO DE INGENIERÍA: Forzamos la fecha manual rompiendo el bloqueo de auto_now_add
            fecha_retroactiva = form.cleaned_data.get('fecha_manual')
            if fecha_retroactiva and request.user.is_staff:
                # Modificación directa en la base de datos por SQL/ORM sin pasar por validaciones de modelo
                Venta.objects.filter(pk=venta.id).update(fecha_emision=fecha_retroactiva)
                
                # Recargamos la instancia para obligar al cliente a recalcular sus moras con la nueva línea temporal
                venta_actualizada = Venta.objects.get(pk=venta.id)
                venta_actualizada.save() 
            
            messages.success(request, f'Venta #{venta.id} actualizada con éxito en el Core.')
            return redirect('historial_ventas')
    else:
        # Cargamos la fecha original para que se pinte en el input al entrar a editar
        form = VentaForm(instance=venta, initial={
            'fecha_manual': venta.fecha_emision.strftime('%Y-%m-%dT%H:%M') if venta.fecha_emision else None
        })
        
    return render(request, 'registrar_venta.html', {'form': form, 'editando': True, 'venta': venta})

@login_required
def eliminar_venta(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    cliente_afectado = venta.cliente # Guardamos el cliente para el recálculo post-borrado
    
    if request.method == 'POST':
        id_removido = venta.id
        venta.delete()
        
        # Forzamos al cliente a recalcular sus métricas de riesgo ahora que la venta ya no existe
        # Reutilizamos la lógica del save() creando una venta ficticia temporal o guardando al cliente
        moras_reales = Venta.objects.filter(cliente=cliente_afectado, estado_pago='EN_MORA').count()
        cliente_afectado.incidencias_mora_total = moras_reales
        total_diferidos = cliente_afectado.compras_realizadas.count()
        
        if total_diferidos > 0:
            factor = cliente_afectado.categoria_riesgo.factor_severidad if cliente_afectado.categoria_riesgo else 1.0
        else:
            cliente_afectado.incidencias_mora_total = 0
            
        cliente_afectado.save()
        
        messages.warning(request, f'La venta #{id_removido} ha sido eliminada del sistema de auditoría.')
        return redirect('historial_ventas')
        
    return render(request, 'confirmar_eliminar_venta.html', {'venta': venta})

@login_required
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
    # Capturamos el cliente desde los parámetros de la URL (?cliente_id=...)
    cliente_id = request.GET.get('cliente_id')
    cliente = get_object_or_404(Cliente, pk=cliente_id) if cliente_id else None

    # El sistema analiza los casos de éxito del pasado para este perfil de riesgo
    recomendacion_cbr = None
    if cliente:
        recomendacion_cbr = motor_cbr_recomendar_tecnica(cliente)

    # Si el formulario se envía, lo procesamos normalmente y guardamos la gestión de mora
    if request.method == 'POST':
        form = HistorialGestionForm(request.POST)
        if form.is_valid():
            nueva_gestion = form.save(commit=False)
            
            # Si el cliente no venía en la URL pero el formulario lo tiene, lo asignamos
            if cliente:
                nueva_gestion.cliente = cliente
            
            nueva_gestion.save()
            calcular_scoring_riesgo(nueva_gestion.cliente)
            # Mensaje de éxito informando el registro de la auditoría
            messages.success(request, f'Gestión de cobranza registrada con éxito para {nueva_gestion.cliente.nombres}.')
            return redirect('ver_historial_cliente', cliente_id=nueva_gestion.cliente.id)
    else:
        # Si ya conocemos al cliente por la URL, podemos pre-llenar el formulario u ocultar el campo
        form = HistorialGestionForm(initial={'cliente': cliente}) if cliente else HistorialGestionForm()

    # Enviamos los resultados del Core ('cbr') directo al contexto de la plantilla
    contexto = {
        'form': form,
        'cliente': cliente,
        'cbr': recomendacion_cbr  # Contiene: 'recomendacion', 'mensaje' y 'confianza'
    }
    
    return render(request, 'registrar_gestion.html', contexto)

@login_required
def editar_gestion_mora(request, pk):
    gestion = get_object_or_404(HistorialGestion, pk=pk)
    cliente = gestion.cliente
    
    # Mantenemos el asistente CBR visible incluso al editar
    recomendacion_cbr = motor_cbr_recomendar_tecnica(cliente)

    if request.method == 'POST':
        form = HistorialGestionForm(request.POST, instance=gestion)
        if form.is_valid():
            form.save()
            messages.success(request, f'Registro de gestión actualizado con éxito para {cliente.nombres}.')
            return redirect('ver_historial_cliente', cliente_id=cliente.id)
    else:
        form = HistorialGestionForm(instance=gestion)

    contexto = {
        'form': form,
        'cliente': cliente,
        'cbr': recomendacion_cbr,
        'editando': True,
        'gestion': gestion
    }
    return render(request, 'registrar_gestion.html', contexto)

@login_required
def eliminar_gestion_mora(request, pk):
    gestion = get_object_or_404(HistorialGestion, pk=pk)
    cliente_id = gestion.cliente.id # Guardamos el ID antes de borrar para poder redireccionar
    
    if request.method == 'POST':
        gestion.delete()
        messages.warning(request, 'La intervención ha sido eliminada del expediente.')
        return redirect('ver_historial_cliente', cliente_id=cliente_id)
        
    return render(request, 'confirmar_eliminar_gestion.html', {'gestion': gestion})

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
    return redirect('principal_panel')

@login_required
def editar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        producto.nombre = request.POST.get('nombre')
        producto.precio = request.POST.get('precio')
        producto.stock = request.POST.get('stock')
        producto.save()
        return redirect('principal_panel')
    return render(request, 'editar_producto.html', {'producto': producto})

@login_required
def eliminar_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    if request.method == 'POST':
        producto.delete()
    return redirect('principal_panel')

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


#==================================================
# 10. ENDPOINT AJAX: OBTENER PRECIO DE PRODUCTO
#==================================================

def ajax_obtener_precio_producto(request):
    producto_id = request.GET.get('producto_id')
    try:
        producto = Producto.objects.get(id=producto_id)
        return JsonResponse({'precio': str(producto.precio)})
    except Producto.DoesNotExist:
        return JsonResponse({'precio': '0.00'})