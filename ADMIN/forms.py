"""Filtros del directorio con el mismo catálogo de roles mostrado en pantalla."""

import datetime
import re

from django import forms
from django.http import QueryDict


class FiltrosUsuariosForm(forms.Form):
    q = forms.CharField(label="Búsqueda", required=False, max_length=100)
    estado = forms.ChoiceField(
        label="Estado",
        required=False,
        choices=[("", "Todos"), ("activo", "Activos"), ("inactivo", "Inactivos")],
        error_messages={"invalid_choice": "Selecciona un estado válido."},
    )
    rol = forms.ChoiceField(label="Rol", required=False, error_messages={"invalid_choice": "Selecciona un rol válido."})

    def __init__(self, data=None, *, grupos):
        super().__init__(data)
        self.fields["rol"].choices = [("", "Todos los roles"), *[(str(g.pk), g.name) for g in grupos]]

    def consulta_url(self, *, pagina=1):
        if not self.is_valid():
            return ""
        params = QueryDict(mutable=True)
        for nombre in self.fields:
            if valor := self.cleaned_data.get(nombre):
                params[nombre] = valor
        if pagina > 1:
            params["page"] = pagina
        return "?" + params.urlencode() if params else ""


class FiltrosAuditoriaForm(forms.Form):
    q = forms.CharField(
        label="Buscar actividad",
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={"data-live-input": True, "placeholder": "Nombre, cuenta, acción o ruta…"}),
    )
    estado = forms.ChoiceField(
        label="Tipo de registro",
        required=False,
        choices=[
            ("", "Todos los registros"),
            ("http", "Solicitudes HTTP"),
            ("incidencias", "Respuestas HTTP 400–599"),
            ("internos", "Registros internos"),
        ],
        error_messages={"invalid_choice": "Selecciona un tipo de registro válido."},
    )
    desde = forms.CharField(
        label="Desde",
        required=False,
        max_length=10,
        widget=forms.TextInput(attrs={"type": "date", "min": "1000-01-01", "max": "9998-12-31"}),
    )
    hasta = forms.CharField(
        label="Hasta",
        required=False,
        max_length=10,
        widget=forms.TextInput(attrs={"type": "date", "min": "1000-01-01", "max": "9998-12-31"}),
    )

    def _fecha(self, nombre):
        value = self.cleaned_data[nombre]
        if not value:
            return None
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) and 1000 <= int(value[:4]) <= 9998:
            try:
                return datetime.date.fromisoformat(value)
            except ValueError:
                pass
        raise forms.ValidationError("Elige una fecha válida entre 1000-01-01 y 9998-12-31.")

    def clean_desde(self):
        return self._fecha("desde")

    def clean_hasta(self):
        return self._fecha("hasta")

    def clean(self):
        datos = super().clean()
        if datos.get("desde") and datos.get("hasta") and datos["desde"] > datos["hasta"]:
            self.add_error("hasta", "La fecha final debe ser igual o posterior a la inicial.")
        return datos

    def consulta_url(self):
        params = QueryDict(mutable=True)
        datos = self.cleaned_data if self.is_valid() else self.data
        for nombre in self.fields:
            valor = datos.get(nombre)
            if valor not in (None, ""):
                params[nombre] = valor.isoformat() if isinstance(valor, datetime.date) else valor
        return "?" + params.urlencode() if params else ""
