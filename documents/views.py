import hashlib
import json
import math
from datetime import date
from pathlib import Path

from django.contrib import messages
from django.db import transaction
from django.http import FileResponse, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .forms import TemplateForm, UploadForm
from .models import Document, ExtractionTemplate
from .services.exports import build_xlsx, effective_fields, export_payload

@require_http_methods(['GET', 'POST'])
def index(request):
    form = UploadForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        upload = form.cleaned_data['file']
        selected = form.cleaned_data['template']
        digest = hashlib.sha256()
        for chunk in upload.chunks():
            digest.update(chunk)
        upload.seek(0)
        document = Document(template=selected, template_snapshot={'name': selected.name, 'fields': selected.fields},
                            original_name=Path(upload.name).name[:255], file_size=upload.size, sha256=digest.hexdigest())
        # File names on disk are random; keep the user-facing filename in DB.
        try:
            document.original.save(upload.name, upload, save=False)
            document.save()
        except Exception:
            if document.original.name:
                document.original.delete(save=False)
            raise
        messages.success(request, 'Documento conservato e aggiunto alla coda di estrazione.')
        return redirect('documents:detail', pk=document.pk)
    counts = {state: Document.objects.filter(status=state).count() for state in Document.Status.values}
    return render(request, 'documents/index.html', {'form': form, 'documents': Document.objects.all()[:50], 'template_count': ExtractionTemplate.objects.count(), 'counts': counts})

@require_GET
def template_list(request):
    return render(request, 'documents/template_list.html', {'extraction_templates': ExtractionTemplate.objects.all()})

@require_http_methods(['GET', 'POST'])
def template_form(request, pk=None):
    instance = get_object_or_404(ExtractionTemplate, pk=pk) if pk else None
    form = TemplateForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Template salvato. I documenti già caricati mantengono la loro versione dei campi.')
        return redirect('documents:template_list')
    return render(request, 'documents/template_form.html', {'form': form, 'edit': bool(pk)})

def _review_text(value, kind):
    if value is None:
        return ''
    if kind == 'list' and isinstance(value, list):
        return '\n'.join(str(item) for item in value)
    return str(value)

@require_GET
def detail(request, pk):
    document = get_object_or_404(Document, pk=pk)
    fields = effective_fields(document)
    for field in fields:
        field['review_value'] = _review_text(field.get('value'), field['type'])
        field['display_value'] = field['review_value'] or 'Non trovato'
    return render(request, 'documents/detail.html', {
        'document': document, 'fields': fields,
        'segments': document.extracted.get('segments', []),
        'warnings': document.extracted.get('warnings', []) + document.result.get('warnings', []),
        'reviewed': bool(document.overrides), 'can_export': document.status == Document.Status.SUCCEEDED,
        'original_exists': bool(document.original and document.original.storage.exists(document.original.name)),
    })

def _parse_review(value, kind):
    value = value.strip()
    if not value:
        return None
    if len(value) > 10000:
        raise ValueError('Un campo supera il limite di 10.000 caratteri.')
    if kind == 'list':
        values = [item.strip() for item in value.splitlines() if item.strip()]
        if len(values) > 100:
            raise ValueError('Un elenco può contenere al massimo 100 elementi.')
        return values
    if kind == 'number':
        # Accept JSON notation; UI tells the user to use a dot for decimals.
        result = json.loads(value)
        if isinstance(result, bool) or not isinstance(result, (int, float)) or not math.isfinite(result):
            raise ValueError('Inserisci un numero valido usando il punto per i decimali, senza simboli di valuta.')
        return result
    if kind == 'date':
        date.fromisoformat(value)
    return value

@require_POST
def review(request, pk):
    with transaction.atomic():
        document = get_object_or_404(Document.objects.select_for_update(), pk=pk)
        if document.status != Document.Status.SUCCEEDED:
            return HttpResponseBadRequest('Il documento non è ancora pronto per la revisione.')
        overrides = {}
        try:
            for field in document.template_snapshot['fields']:
                name = 'field_' + field['key']
                if name not in request.POST:
                    return HttpResponseBadRequest('La revisione deve includere tutti i campi.')
                value = _parse_review(request.POST[name], field['type'])
                overrides[field['key']] = {'value': value, 'reviewed_at': timezone.now().isoformat()}
        except (ValueError, TypeError, OverflowError):
            messages.error(request, 'Valore non valido: usa date AAAA-MM-GG, numeri senza valuta e un elemento per riga negli elenchi.')
            return redirect('documents:detail', pk=pk)
        document.overrides = overrides
        document.save(update_fields=['overrides', 'updated_at'])
    messages.success(request, 'Revisione salvata. I risultati automatici e le loro fonti restano disponibili nelle esportazioni.')
    return redirect('documents:detail', pk=pk)

@require_POST
def retry(request, pk):
    changed = Document.objects.filter(pk=pk, status=Document.Status.FAILED).update(
        status=Document.Status.QUEUED, error='', result={}, overrides={}, started_at=None, completed_at=None)
    get_object_or_404(Document, pk=pk)
    if changed:
        messages.success(request, 'Documento rimesso in coda con il template originale.')
    return redirect('documents:detail', pk=pk)

@require_POST
def delete(request, pk):
    with transaction.atomic():
        document = get_object_or_404(Document.objects.select_for_update(), pk=pk)
        if document.status == Document.Status.PROCESSING:
            messages.error(request, 'Attendi il termine dell’elaborazione prima di eliminare il documento.')
            return redirect('documents:detail', pk=pk)
        original = document.original
        document.delete()
        transaction.on_commit(lambda: original.delete(save=False))
    messages.success(request, 'Documento, originale e risultati eliminati dall’app. Le copie già esportate restano nei tuoi file.')
    return redirect('documents:index')

@require_GET
def original(request, pk):
    document = get_object_or_404(Document, pk=pk)
    if not document.original or not document.original.storage.exists(document.original.name):
        return HttpResponse('Originale non disponibile.', status=404)
    return FileResponse(document.original.open('rb'), as_attachment=True, filename=document.original_name)

@require_GET
def status(request, pk):
    document = get_object_or_404(Document, pk=pk)
    return JsonResponse({'status': document.status, 'label': document.get_status_display()})

def _exportable(pk):
    document = get_object_or_404(Document, pk=pk)
    return document if document.status == Document.Status.SUCCEEDED else None

@require_GET
def export_json(request, pk):
    document = _exportable(pk)
    if not document:
        return HttpResponseBadRequest('Il risultato non è ancora disponibile.')
    response = JsonResponse(export_payload(document), json_dumps_params={'ensure_ascii': False, 'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="document-{document.pk}.json"'
    return response

@require_GET
def export_xlsx(request, pk):
    document = _exportable(pk)
    if not document:
        return HttpResponseBadRequest('Il risultato non è ancora disponibile.')
    response = HttpResponse(build_xlsx(document), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="document-{document.pk}.xlsx"'
    return response
