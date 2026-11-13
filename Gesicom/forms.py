from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.validators import URLValidator

from notificaciones.models import PlazoReporte
from notificaciones.services import plazos_para_usuario

from .adjuntos import EXTENSIONES_EVIDENCIA, MAX_ARCHIVO
from .models import Envio
from .solicitudes import crear_solicitud, verificar_solicitud
from .validators import validar_archivo_evidencia

User = get_user_model()


class BusquedaGlobalForm(forms.Form):
    q = forms.CharField(label="Buscar en GESICOM", required=False, max_length=100)


class EvidenciaForm(forms.Form):
    solicitud = forms.CharField(required=False, widget=forms.HiddenInput)
    nombre = forms.CharField(label="Nombre de la evidencia", max_length=80)
    proyecto = forms.ChoiceField(label="Proyecto", choices=[("", "Selecciona un proyecto"), *Envio.PROYECTO_CHOICES])
    plazo = forms.ModelChoiceField(
        label="Plazo de reporte (opcional)",
        queryset=PlazoReporte.objects.none(),
        required=False,
        empty_label="Evidencia sin plazo asociado",
    )
    evidencias = forms.MultipleChoiceField(
        label="Tipo de evidencia",
        choices=[(tipo, tipo) for tipo in ["Planeación", "Ejecución", "Evaluación", "Informe Final", "Documento"]],
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    linkArchivo = forms.CharField(
        label="Enlace de la evidencia",
        required=False,
        max_length=200,
        validators=[URLValidator(schemes=["http", "https"])],
        widget=forms.URLInput(attrs={"placeholder": "https://"}),
    )
    archivo = forms.FileField(label="Archivo de la evidencia", required=False, validators=[validar_archivo_evidencia])
    eliminar_archivo = forms.BooleanField(label="Retirar el archivo actual", required=False)
    observaciones = forms.CharField(
        label="Observaciones (opcional)", max_length=2000, required=False, widget=forms.Textarea
    )
    motivo = forms.CharField(
        label="¿Qué corregiste?",
        min_length=3,
        max_length=1000,
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    version = forms.IntegerField(min_value=1, required=False, widget=forms.HiddenInput)

    def __init__(self, data=None, files=None, *, usuario, envio=None, **kwargs):
        self.envio = envio
        self.usuario = usuario
        if data is not None and not data.get("linkArchivo") and data.get("link_evidencia"):
            data = data.copy()
            data["linkArchivo"] = data["link_evidencia"]
        super().__init__(data, files, **kwargs)
        from django.utils import timezone

        self.fields["plazo"].label_from_instance = lambda plazo: (
            f"{plazo.titulo} · {timezone.localtime(plazo.fecha_limite):%d/%m/%Y %H:%M}"
            + (" · Fuera de plazo" if plazo.vencido else "")
        )
        self.fields["archivo"].widget.attrs.update(
            {"accept": ",".join(sorted(EXTENSIONES_EVIDENCIA)), "data-file-input": True, "data-max-bytes": MAX_ARCHIVO}
        )
        self.fields["observaciones"].widget.attrs.update({"rows": 4})
        self.fields["plazo"].queryset = plazos_para_usuario(usuario)
        if envio:
            if not envio.proyecto:
                self.fields["proyecto"].required = False
                self.fields["proyecto"].choices = [("", "Sin proyecto (registro anterior)"), *Envio.PROYECTO_CHOICES]
            if envio.proyecto not in dict(self.fields["proyecto"].choices):
                self.fields["proyecto"].choices = [
                    *self.fields["proyecto"].choices,
                    (envio.proyecto, envio.proyecto or "Sin proyecto"),
                ]
            tipos = [
                tipo.strip()
                for tipo in envio.tipo_evidencia.split(",")
                if tipo.strip() and tipo.strip() != "Sin especificar"
            ]
            existentes = {value for value, _ in self.fields["evidencias"].choices}
            self.fields["evidencias"].choices += [(tipo, tipo) for tipo in tipos if tipo not in existentes]
            self.initial.update(
                nombre=envio.nombre,
                proyecto=envio.proyecto,
                plazo=envio.plazo_id,
                evidencias=tipos,
                linkArchivo=envio.link_evidencia,
                version=envio.version,
            )
            self.fields["plazo"].queryset = PlazoReporte.objects.filter(pk=envio.plazo_id)
            self.fields["plazo"].disabled = True
            self.fields["version"].required = True
            self.fields["motivo"].required = True
            self.fields.pop("observaciones")
            self.fields.pop("solicitud")
        else:
            self.initial["solicitud"] = crear_solicitud(usuario)
            for name in ("eliminar_archivo", "motivo", "version"):
                self.fields.pop(name)

    def clean_solicitud(self):
        valor = self.cleaned_data.get("solicitud")
        return verificar_solicitud(valor, self.usuario) if valor else None

    def clean(self):
        data = super().clean()
        archivo_previo = self.envio and self.envio.archivo_evidencia and not data.get("eliminar_archivo")
        if not (data.get("linkArchivo") or data.get("archivo") or archivo_previo):
            self.add_error(None, "Debe proporcionar un enlace o adjuntar un archivo (al menos uno).")
        plazo = data.get("plazo")
        if (
            plazo
            and plazo.proyecto
            and data.get("proyecto") != plazo.proyecto
            and (not self.envio or data.get("proyecto") != self.envio.proyecto)
        ):
            self.add_error("proyecto", "El proyecto debe coincidir con el plazo seleccionado.")
        if len(", ".join(data.get("evidencias", []))) > 50:
            self.add_error("evidencias", "La combinación de tipos supera los 50 caracteres permitidos.")
        return data


class ProfileForm(forms.ModelForm):
    nombre = forms.CharField(label="Nombre", max_length=150)
    apellido = forms.CharField(label="Apellido", max_length=150)
    correo = forms.EmailField(label="Correo electrónico")
    contrasena = forms.CharField(
        label="Nueva contraseña (opcional)",
        required=False,
        strip=False,
        widget=forms.PasswordInput,
        help_text="Mínimo 8 caracteres, con un número o símbolo.",
    )
    confirmar_contrasena = forms.CharField(
        label="Confirma la nueva contraseña",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    contrasena_actual = forms.CharField(
        label="Contraseña actual",
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
        help_text="Necesaria para modificar tu correo, usuario o contraseña.",
    )

    class Meta:
        model = User
        fields = ["username"]
        labels = {"username": "Nombre de usuario"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.correo_anterior = self.instance.email
        self.usuario_anterior = self.instance.username
        self.cambio_sensible = False
        self.fields["contrasena"].widget.attrs["autocomplete"] = "new-password"
        for alias, field in [("nombre", "first_name"), ("apellido", "last_name"), ("correo", "email")]:
            self.fields[alias].initial = getattr(self.instance, field)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input-linea"

    def clean_correo(self):
        email = self.cleaned_data["correo"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Ese correo ya está registrado.")
        return email

    def clean(self):
        data = super().clean()
        self.cambio_sensible = (
            bool(data.get("contrasena"))
            or data.get("correo", "").casefold() != self.correo_anterior.casefold()
            or data.get("username", "") != self.usuario_anterior
        )
        if self.cambio_sensible and not self.instance.check_password(data.get("contrasena_actual", "")):
            self.add_error("contrasena_actual", "Confirma tu contraseña actual para realizar este cambio.")
        if data.get("contrasena") and data.get("contrasena") != data.get("confirmar_contrasena"):
            self.add_error("confirmar_contrasena", "Las contraseñas no coinciden.")
        self.instance.username = data.get("username", self.instance.username)
        self.instance.first_name = data.get("nombre", "")
        self.instance.last_name = data.get("apellido", "")
        self.instance.email = data.get("correo", "")
        if data.get("contrasena"):
            try:
                validate_password(data["contrasena"], self.instance)
            except forms.ValidationError as error:
                self.add_error("contrasena", error)
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data["contrasena"]:
            user.set_password(self.cleaned_data["contrasena"])
        if commit:
            user.save()
        return user
