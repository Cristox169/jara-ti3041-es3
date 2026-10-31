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
    PrecioProducto,
    Producto,
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
            "punto_reorden",
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
