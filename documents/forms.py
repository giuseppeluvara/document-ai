import json
import zipfile
from pathlib import Path
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from .models import ExtractionTemplate
from .schema import validate_fields

DEFAULT_FIELDS = [
    {'key': 'parti', 'label': 'Parti', 'description': 'Nomi delle parti che stipulano il contratto.', 'type': 'list'},
    {'key': 'oggetto', 'label': 'Oggetto', 'description': 'Oggetto del contratto, usando le parole del documento.', 'type': 'text'},
    {'key': 'importo', 'label': 'Importo', 'description': 'Importo principale del contratto, se esplicitamente indicato.', 'type': 'number'},
    {'key': 'durata', 'label': 'Durata', 'description': 'Durata contrattuale indicata espressamente.', 'type': 'text'},
    {'key': 'scadenze', 'label': 'Scadenze', 'description': 'Scadenze e relative condizioni esplicitamente indicate.', 'type': 'list'},
]

class TemplateForm(forms.ModelForm):
    fields_json = forms.CharField(label='Campi del template', widget=forms.Textarea(attrs={'rows': 15}), help_text='Da 1 a 12 campi, ciascuno con key, label, description e type.')
    class Meta:
        model = ExtractionTemplate
        fields = ['name', 'description']
        widgets = {'description': forms.Textarea(attrs={'rows': 2})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fields_json'].initial = json.dumps(self.instance.fields if self.instance.pk else DEFAULT_FIELDS, ensure_ascii=False, indent=2)
    def clean_fields_json(self):
        try:
            data = json.loads(self.cleaned_data['fields_json'])
        except (ValueError, TypeError):
            raise forms.ValidationError('Il JSON dei campi non è valido.')
        return validate_fields(data)
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.fields = self.cleaned_data['fields_json']
        if commit:
            instance.save()
        return instance

class UploadForm(forms.Form):
    file = forms.FileField(label='Documento PDF o Word', widget=forms.ClearableFileInput(attrs={'accept': '.pdf,.docx'}))
    template = forms.ModelChoiceField(label='Template di estrazione', queryset=ExtractionTemplate.objects.all(), empty_label='Scegli un template')
    def clean_file(self):
        upload = self.cleaned_data['file']
        suffix = Path(upload.name).suffix.lower()
        if suffix not in {'.pdf', '.docx'}:
            raise ValidationError('Carica un PDF oppure un file Word .docx. I file .doc vanno convertiti in .docx.')
        if not upload.size or upload.size > settings.DOCUMENT_AI_MAX_UPLOAD_MB * 1024 * 1024:
            raise ValidationError(f'Il file deve avere una dimensione compresa tra 1 byte e {settings.DOCUMENT_AI_MAX_UPLOAD_MB} MB.')
        if suffix == '.pdf':
            signature = upload.read(1024)
            if b'%PDF-' not in signature:
                raise ValidationError('Il contenuto non corrisponde a un PDF valido.')
        else:
            try:
                with zipfile.ZipFile(upload) as archive:
                    if 'word/document.xml' not in archive.namelist():
                        raise ValueError()
            except (zipfile.BadZipFile, ValueError, OSError):
                raise ValidationError('Il contenuto non corrisponde a un documento Word .docx valido.')
        upload.seek(0)
        return upload
