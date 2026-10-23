from django.core.management.base import BaseCommand
from documents.forms import DEFAULT_FIELDS
from documents.models import ExtractionTemplate

class Command(BaseCommand):
    help = 'Crea un template Contratto modificabile, senza sovrascrivere i template esistenti.'
    def handle(self, *args, **options):
        _, created = ExtractionTemplate.objects.get_or_create(name='Contratto', defaults={'description': 'Parti, oggetto, importo, durata e scadenze. Personalizzabile.', 'fields': DEFAULT_FIELDS})
        self.stdout.write('Template Contratto creato.' if created else 'Template già presente: nessuna modifica.')
