from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Cliente, CategoriaRiesgo, Diferido, PerfilSocioeconomico, Producto, TecnicaMejora, HistorialGestion, Venta, Vendedor

# ---------------------------------------------------------
# 1. FORMULARIO DE CLIENTE
# ---------------------------------------------------------
class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['identificacion', 'nombres', 'categoria_riesgo']
        # WIDGETS: Evitamos inputs simples. Forzamos un dropdown para la llave foránea.
        widgets = {
            'identificacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 17xxxxxxx'}),
            'nombres': forms.TextInput(attrs={'class': 'form-control'}),
            'categoria_riesgo': forms.Select(attrs={'class': 'form-select'}) # Dropdown dependiente de la DB
        }

    # Validación Back-End de dato sensible 
    def clean_identificacion(self):
        cedula = self.cleaned_data.get('identificacion')

        if not cedula.isdigit():
            raise ValidationError("La cédula debe contener únicamente números, sin guiones ni espacios.")
        
        if len(cedula) != 10:
            raise ValidationError(f"La cédula debe tener 10 dígitos. Has ingresado {len(cedula)}.")

        provincia = int(cedula[0:2])
        if provincia < 1 or (provincia > 24 and provincia != 30):
            raise ValidationError("El código de provincia de la cédula es inválido.")

        return cedula


# ---------------------------------------------------------
# 2. FORMULARIO DE CATEGORÍA DE RIESGO
# ---------------------------------------------------------
class CategoriaRiesgoForm(forms.ModelForm):
    class Meta:
        model = CategoriaRiesgo
        fields = ['codigo', 'descripcion', 'factor_severidad']
        widgets = {
            'codigo': forms.Select(attrs={'class': 'form-control'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'factor_severidad': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
        }

    # Validación Back-End: El factor de severidad es crítico para la ecuación CBR
    def clean_factor_severidad(self):
        factor = self.cleaned_data.get('factor_severidad')
        if factor <= 0:
            raise ValidationError("El factor de severidad no puede ser cero o negativo. Arruinaría el cálculo del Scoring.")
        return factor

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo')
        return codigo.upper() # Sanitización: Siempre guardar en mayúsculas


# ---------------------------------------------------------
# 3. FORMULARIO DE DIFERIDO
# ---------------------------------------------------------
class DiferidoForm(forms.ModelForm):
    class Meta:
        model = Diferido
        fields = ['meses_plazo', 'porcentaje_interes', 'requiere_entrada']
        widgets = {
            'meses_plazo': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'porcentaje_interes': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'requiere_entrada': forms.CheckboxInput(attrs={'class': 'form-check-input'}) # Input tipo Checkbox
        }

    # Validación Back-End: Lógica financiera
    def clean_meses_plazo(self):
        meses = self.cleaned_data.get('meses_plazo')
        if meses <= 0 or meses > 48:
            raise ValidationError("El plazo diferido debe ser entre 1 y 48 meses.")
        return meses

    def clean_porcentaje_interes(self):
        interes = self.cleaned_data.get('porcentaje_interes')
        if interes < 0:
            raise ValidationError("El porcentaje de interés no puede ser un valor negativo.")
        return interes


# ---------------------------------------------------------
# 4. FORMULARIO DE TÉCNICA DE MEJORA
# ---------------------------------------------------------
class TecnicaMejoraForm(forms.ModelForm):
    class Meta:
        model = TecnicaMejora
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}) # Textarea en vez de input simple
        }


# ---------------------------------------------------------
# 5. FORMULARIO DE HISTORIAL DE GESTIÓN (Motor CBR)
# ---------------------------------------------------------
class HistorialGestionForm(forms.ModelForm):
    class Meta:
        model = HistorialGestion
        fields = ['cliente', 'tecnica', 'fue_exitosa', 'observaciones']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}), # Dropdown de clientes
            'tecnica': forms.Select(attrs={'class': 'form-select'}), # Dropdown de técnicas
            'fue_exitosa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2})
        }

    # Validación Back-End
    def clean_observaciones(self):
        observaciones = self.cleaned_data.get('observaciones')
        fue_exitosa = self.cleaned_data.get('fue_exitosa')
        
        if not fue_exitosa and (not observaciones or len(observaciones.strip()) < 5):
            raise ValidationError("Si la gestión no fue exitosa, debe ingresar una observación detallando el motivo.")
        return observaciones


# ---------------------------------------------------------
# 6. FORMULARIO DE VENTA
# ---------------------------------------------------------

class VentaForm(forms.ModelForm):
    # 1. Definimos 'producto' como un campo extra, FUERA de la clase Meta.
    # Así Django sabe que debe mostrarlo en el HTML, pero no intentará guardarlo directamente en Venta.
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.all(),
        required=False, # Ponlo en True si es obligatorio seleccionar un producto inicial
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    fecha_manual = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control', 
            'type': 'datetime-local',
            'style': 'background-color: #FEF3C7; border: 1px solid #F59E0B;' # Color sutil ámbar de auditoría
        }),
        help_text="Opcional: Use este campo SOLO si desea anular la fecha actual del sistema (Retroactivos)."
    )
    
    class Meta:
        model = Venta
        # 2. BORRAMOS 'producto' de esta lista porque no pertenece al modelo Venta
        fields = ['colaborador', 'cliente', 'diferido', 'estado_pago', 'total_pagar', 'descripcion_venta', 'fecha_manual']
        widgets = {
            'colaborador': forms.Select(attrs={'class': 'form-select'}),
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'diferido': forms.Select(attrs={'class': 'form-select'}), # Este dropdown se llenará vía AJAX
            'estado_pago': forms.Select(attrs={'class': 'form-select'}),
            # 3. Borramos el widget de producto de aquí también
            'total_pagar': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'descripcion_venta': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Este ciclo añade el precio de la DB a la etiqueta HTML <option>
        # Ahora funcionará perfectamente porque 'producto' está definido arriba
        if 'producto' in self.fields:
            self.fields['producto'].widget.choices = [
                (p.id, p.nombre) for p in Producto.objects.all()
            ]

    # Validación Back-End Maestra: Integrando las reglas de negocio del PDF
    def clean(self):
        cleaned_data = super().clean()
        cliente = cleaned_data.get("cliente")
        diferido = cleaned_data.get("diferido")

        if cliente and cliente.categoria_riesgo:
            riesgo = cliente.categoria_riesgo.codigo
            
            # REGLA PDF: Riesgo Crítico deshabilita planes a largo plazo 
            if riesgo == 'CRITICO' and diferido:
                if diferido.meses_plazo > 3:
                    raise ValidationError(f"Operación denegada: El cliente {cliente.nombres} tiene riesgo CRÍTICO. No se permiten diferidos mayores a 3 meses.")
            
            # REGLA PDF: Riesgo Medio exige enganche (entrada) 
            elif riesgo == 'MEDIO' and diferido:
                if not diferido.requiere_entrada:
                    raise ValidationError(f"Operación denegada: El cliente {cliente.nombres} tiene riesgo MEDIO. El plan diferido seleccionado debe requerir entrada/enganche obligatoriamente.")
        
        return cleaned_data
    
# VENDEDORES/COLABORADORES

class CrearVendedorForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, label="Nombre de Usuario para Login")
    password = forms.CharField(widget=forms.PasswordInput, required=True, label="Contraseña Temporal")

    class Meta:
        model = Vendedor
        fields = ['nombre_completo', 'email']

    @transaction.atomic # Asegura que si falla una tabla, no se guarde la otra por error
    def save(self, commit=True):
        # 1. Crear la cuenta de acceso de Django
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password']
        )
        
        # 2. Crear el perfil de Vendedor y enlazarlo
        vendedor = super().save(commit=False)
        vendedor.user = user
        
        if commit:
            vendedor.save()
        return vendedor
    
class EditarVendedorForm(forms.ModelForm):
    username = forms.CharField(max_length=150, required=True, label="Nombre de Usuario (Login)")

    class Meta:
        model = Vendedor
        fields = ['nombre_completo', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cargamos el username actual de la tabla User al formulario
        if self.instance and hasattr(self.instance, 'user'):
            self.fields['username'].initial = self.instance.user.username

    @transaction.atomic
    def save(self, commit=True):
        # 1. Guardamos los datos del modelo Vendedor
        vendedor = super().save(commit=False)
        
        # 2. Sincronizamos los cambios con el modelo User nativo
        user = vendedor.user
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email'] 
        user.save()
        
        if commit:
            vendedor.save()
        return vendedor
    
# ==============================================
# 8. FORMULARIO DE PERFIL SOCIOECONOMICO
# ==============================================

class PerfilSocioeconomicoForm(forms.ModelForm):
    class Meta:
        model = PerfilSocioeconomico
        fields = [
            'estado_civil',
            'tiene_hijos',
            'numero_hijos', 
            'tipo_trabajo',
            'ingreso_mensual',
            'gastos_fijos_estimados',
            'nivel_estudio'
        ]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})