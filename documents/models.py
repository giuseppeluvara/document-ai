import uuid
from pathlib import Path
from django.db import models
from .schema import validate_fields

def original_path(instance, filename):
    return f'{instance.id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'

class ExtractionTemplate(models.Model):
    name = models.CharField('Nome', max_length=100, unique=True)
    description = models.CharField('Descrizione', max_length=300, blank=True)
    fields = models.JSONField(default=list, validators=[validate_fields])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['name']
    def __str__(self):
        return self.name

class Document(models.Model):
    class Status(models.TextChoices):
        QUEUED = 'queued', 'In coda'
        PROCESSING = 'processing', 'In elaborazione'
        SUCCEEDED = 'succeeded', 'Da verificare'
        FAILED = 'failed', 'Elaborazione non riuscita'
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(ExtractionTemplate, null=True, on_delete=models.SET_NULL)
    template_snapshot = models.JSONField(default=dict)
    original = models.FileField(upload_to=original_path)
    original_name = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True)
    extracted = models.JSONField(default=dict)
    result = models.JSONField(default=dict)
    overrides = models.JSONField(default=dict)
    error = models.TextField(blank=True)
    metrics = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']
