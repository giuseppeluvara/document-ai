import time
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from documents.models import Document
from .ai import AIError, run_extraction
from .ingest import IngestionError, extract_document

def claim_next():
    # Single worker is enforced by an OS lock. Conditional update also avoids
    # claiming the same row if a caller inadvertently races another consumer.
    candidate = Document.objects.filter(status=Document.Status.QUEUED).order_by('created_at').first()
    if not candidate:
        return None
    changed = Document.objects.filter(pk=candidate.pk, status=Document.Status.QUEUED).update(
        status=Document.Status.PROCESSING, started_at=timezone.now(), completed_at=None, error='')
    return Document.objects.get(pk=candidate.pk) if changed else None

def process_document(document):
    started = time.monotonic()
    try:
        document.extracted = extract_document(
            Path(document.original.path), ocr_language=settings.DOCUMENT_AI_OCR_LANGUAGE,
            max_pages=settings.DOCUMENT_AI_MAX_PAGES, max_chars=settings.DOCUMENT_AI_MAX_CHARS)
        document.save(update_fields=['extracted', 'updated_at'])
        document.result = run_extraction(
            document.extracted['segments'], document.template_snapshot['fields'],
            endpoint=settings.DOCUMENT_AI_ENDPOINT, model=settings.DOCUMENT_AI_MODEL,
            timeout=settings.DOCUMENT_AI_TIMEOUT, context_chars=settings.DOCUMENT_AI_CONTEXT_CHARS,
            max_tokens=settings.DOCUMENT_AI_MAX_TOKENS)
        document.status = Document.Status.SUCCEEDED
        document.error = ''
    except (AIError, IngestionError) as exc:
        document.status = Document.Status.FAILED
        document.error = str(exc)[:1500]
    except Exception:
        # Exceptions from parsers or providers may contain document contents.
        # Never write raw exception strings or response payloads to the UI/log.
        document.status = Document.Status.FAILED
        document.error = 'Errore inatteso durante l’elaborazione. Verifica il file e la configurazione locale, poi riprova.'
    document.completed_at = timezone.now()
    document.metrics = {
        'elapsed_seconds': round(time.monotonic() - started, 2),
        'segments': len(document.extracted.get('segments', [])),
        'characters': document.extracted.get('text_char_count', 0),
    }
    document.save(update_fields=['result', 'status', 'error', 'completed_at', 'metrics', 'updated_at'])
    return document
