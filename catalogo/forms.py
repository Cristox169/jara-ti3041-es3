from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    Bodega,
    Categoria,
    ConsultaCliente,
    ListaPrecio,
    MovimientoInventario,
    NotaCredito,
    OrdenTrabajo,
    PrecioProducto,
    Producto,
    Cotizacion,
)


class ProductoForm(forms.ModelForm):
    """Formulario web del CRUD; precio y stock se proyectan al esquema normalizado."""

    precio = forms.DecimalField(
        min_value=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        label="Precio de venta",
    )
    stock = forms.DecimalField(
        min_value=Decimal("0"),
        max_digits=12,
        decimal_places=2,
        label="Stock inicial",
    )

    class Meta:
        model = Producto
        fields = (
            "sku",
            "nombre",
            "descripcion",
            "categoria",
            "marca",
            "unidad",
            "stock_minimo",
            "stock_ideal",
            "imagen_url",
            "activo",
            "precio",
            "stock",
        )
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 4}),
            "imagen_url": forms.URLInput(attrs={"placeholder": "https://..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["precio"].initial = self.instance.precio_vigente
            self.fields["stock"].initial = self.instance.stock_total

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if len(nombre) < 3:
            raise ValidationError("El nombre debe tener al menos 3 caracteres.")
        return nombre

    def clean(self):
        cleaned = super().clean()
        minimo = cleaned.get("stock_minimo")
        ideal = cleaned.get("stock_ideal")
        if minimo is not None and ideal is not None and ideal < minimo:
            self.add_error("stock_ideal", "El stock ideal debe ser mayor o igual al stock mínimo.")
        return cleaned

    def save(self, commit=True):
        producto = super().save(commit=False)
        # Mantiene el campo histórico punto_reorden alineado con el nuevo stock mínimo.
        producto.punto_reorden = self.cleaned_data.get("stock_minimo", producto.punto_reorden)
        if commit:
            producto.save()
        return producto


class ConsultaClienteForm(forms.ModelForm):
    class Meta:
        model = ConsultaCliente
        fields = ("nombre", "correo", "producto_interes", "mensaje")
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Tu nombre"}),
            "correo": forms.EmailInput(attrs={"placeholder": "tu@correo.cl"}),
            "producto_interes": forms.Select(),
            "mensaje": forms.Textarea(attrs={"rows": 6, "placeholder": "¿En qué podemos ayudarte?"}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if len(nombre) < 3:
            raise ValidationError("Indica tu nombre completo.")
        return nombre

    def clean_mensaje(self):
        mensaje = self.cleaned_data["mensaje"].strip()
        if len(mensaje) < 10:
            raise ValidationError("El mensaje debe tener al menos 10 caracteres.")
        return mensaje


class CotizacionForm(forms.ModelForm):
    producto = forms.ModelChoiceField(queryset=Producto.objects.filter(activo=True), required=False, label="Producto inicial")
    cantidad = forms.DecimalField(min_value=Decimal("0.01"), required=False, initial=1, label="Cantidad")
    precio_unitario = forms.DecimalField(min_value=Decimal("0"), required=False, label="Precio unitario")

    class Meta:
        model = Cotizacion
        fields = ("cliente", "vigencia_dias", "estado", "observaciones")
        widgets = {"observaciones": forms.Textarea(attrs={"rows": 4})}

    def clean(self):
        cleaned = super().clean()
        producto = cleaned.get("producto")
        cantidad = cleaned.get("cantidad")
        precio = cleaned.get("precio_unitario")
        if producto and not cantidad:
            self.add_error("cantidad", "Indica la cantidad del producto.")
        if producto and precio is None:
            self.add_error("precio_unitario", "Indica el precio unitario.")
        return cleaned


class OrdenTrabajoForm(forms.ModelForm):
    class Meta:
        model = OrdenTrabajo
        fields = (
            "cliente",
            "titulo",
            "descripcion",
            "estado",
            "prioridad",
            "fecha_compromiso",
            "costo_estimado",
        )
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 5}),
            "fecha_compromiso": forms.DateInput(attrs={"type": "date"}),
        }


class NotaCreditoForm(forms.ModelForm):
    class Meta:
        model = NotaCredito
        fields = ("venta", "motivo", "monto", "estado", "referencia_tributaria")
        widgets = {"motivo": forms.Textarea(attrs={"rows": 3})}

    def clean_monto(self):
        monto = self.cleaned_data["monto"]
        venta = self.cleaned_data.get("venta")
        if venta and monto > venta.total:
            raise ValidationError("La nota de crédito no puede superar el total de la venta.")
        return monto


def sincronizar_precio_y_stock(producto, precio, stock, usuario="web"):
    """Persiste los campos del formulario en PrecioProducto y MovimientoInventario."""
    lista, _ = ListaPrecio.objects.get_or_create(
        nombre="Público general", defaults={"moneda": "CLP", "activa": True}
    )
    lista.activa = True
    lista.save(update_fields=["activa"])
    PrecioProducto.objects.update_or_create(
        producto=producto,
        lista=lista,
        vigente_desde=timezone.localdate(),
        defaults={"monto": precio, "vigente_hasta": None},
    )
    bodega, _ = Bodega.objects.get_or_create(
        codigo="TIENDA-01",
        defaults={"nombre": "Tienda principal", "direccion": "Casa matriz", "activa": True},
    )
    actual = producto.stock_total
    diferencia = Decimal(stock) - actual
    if diferencia:
        MovimientoInventario.objects.create(
            producto=producto,
            bodega=bodega,
            tipo=MovimientoInventario.Tipo.AJUSTE,
            cantidad=diferencia,
            costo_unitario=precio,
            referencia="CRUD-WEB",
            observacion=f"Ajuste desde formulario web ({usuario})",
        )
