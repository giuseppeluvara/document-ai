import fcntl
import signal
import time
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from django.utils import timezone
from documents.models import Document
from documents.services.jobs import claim_next, process_document

class Command(BaseCommand):
    help = 'Elabora la coda in sequenza. Un solo worker per directory dati (lock di sistema).'
    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Elabora al massimo un documento, poi termina.')
        parser.add_argument('--poll', type=float, default=2.0, help='Intervallo di polling in secondi (minimo 0.5).')
    def handle(self, *args, **options):
        with (settings.DATA_DIR / 'worker.lock').open('a+') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise CommandError('Un worker è già attivo su questa directory dati.')
            # The exclusive OS lock proves no earlier worker is still alive.
            recovered = Document.objects.filter(status=Document.Status.PROCESSING).update(
                status=Document.Status.FAILED, completed_at=timezone.now(),
                error='Elaborazione interrotta prima del completamento. Usa Riprova per rimettere il documento in coda.')
            if recovered:
                self.stdout.write(f'Ripristinati {recovered} lavori interrotti.')
            self.running = True
            def shutdown(signum, frame):
                self.running = False
            signal.signal(signal.SIGTERM, shutdown)
            signal.signal(signal.SIGINT, shutdown)
            self.stdout.write('Worker attivo: una elaborazione alla volta. Nessun contenuto documentale viene scritto nei log.')
            while self.running:
                close_old_connections()
                document = claim_next()
                if document:
                    result = process_document(document)
                    self.stdout.write(f'{result.id}: {result.status} ({result.metrics["elapsed_seconds"]} s)')
                elif not options['once']:
                    time.sleep(max(0.5, options['poll']))
                if options['once']:
                    break
