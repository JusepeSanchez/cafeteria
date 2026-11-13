from datetime import datetime, timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Categoria, Producto


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ("nombre", "descripcion", "activa")


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ("codigo", "categoria", "nombre", "descripcion", "precio", "stock", "disponible")


class ConfirmarPedidoForm(forms.Form):
    hora_retiro = forms.TimeField(
        input_formats=["%H:%M"],
        widget=forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
    )
    observacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean_hora_retiro(self):
        hora = self.cleaned_data["hora_retiro"]
        if not (8 <= hora.hour < 18 or (hora.hour == 18 and hora.minute == 0)):
            raise ValidationError("La hora de retiro debe estar entre las 08:00 y las 18:00.")
        ahora = timezone.localtime()
        retiro = timezone.make_aware(
            datetime.combine(ahora.date(), hora),
            timezone.get_current_timezone(),
        )
        if retiro < ahora + timedelta(minutes=20):
            raise ValidationError("El retiro debe ser al menos 20 minutos después de ahora.")
        return hora
