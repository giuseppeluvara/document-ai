# Architettura e configurazione

## Componenti

| Componente | Responsabilità |
|---|---|
| Django e interfaccia HTML | Template, caricamento, storico, revisione ed esportazioni |
| SQLite | Metadati, template e coda persistente dei lavori |
| Worker `runworker` | Un lavoro alla volta: estrazione del testo, OCR necessario, chiamate AI e salvataggio |
| pypdf e python-docx | Lettura locale di PDF e DOCX |
| Poppler e Tesseract | Conversione e OCR sequenziale delle pagine scansionate |
| `llama-server` | Un modello GGUF residente, accessibile soltanto via loopback |

L'app conserva l'originale e il testo estratto localmente. Ogni elaborazione usa lo schema dei campi salvato con il lavoro; modificare successivamente un template non deve cambiare il significato di un risultato precedente. Non servono Redis, Celery, Node o database vettoriali per questo flusso.

Il worker e il modello sono servizi separati dal web: una richiesta di caricamento non resta bloccata durante l'inferenza. Il runtime espone un'API locale compatibile con chat completions; si può sostituire il modello senza riscrivere l'interfaccia.

## Template

Un template descrive il risultato desiderato. Esempio dei campi:

```json
[
  {"key": "parti", "label": "Parti", "description": "Persone e società che stipulano il contratto", "type": "list"},
  {"key": "oggetto", "label": "Oggetto", "description": "Oggetto espresso nel contratto", "type": "text"},
  {"key": "importo", "label": "Importo", "description": "Importo contrattuale esplicito", "type": "text"},
  {"key": "scadenze", "label": "Scadenze", "description": "Date e termini espliciti, senza calcolare date implicite", "type": "list"}
]
```

Usare descrizioni precise: «importo totale comprensivo di IVA» distingue il campo da una rata o dall'imponibile. Per importi con valuta e formattazione originale può essere preferibile `text`; i tipi disponibili sono `text`, `number`, `date` e `list`. I limiti sui campi mantengono i prompt adatti al modello piccolo.

Il documento viene suddiviso in porzioni limitate, elaborate in sequenza. Le risposte vengono verificate rispetto ai campi richiesti e alle citazioni. I riferimenti restano associati alla fonte originale; i dati assenti devono rimanere tali. Il controllo delle citazioni e il formato JSON non forniscono una garanzia di accuratezza semantica.

## Variabili d'ambiente

| Variabile | Valore iniziale / funzione |
|---|---|
| `DJANGO_SECRET_KEY` | Se assente, viene generata e conservata localmente in `.data/.secret_key` (o nel percorso dati scelto) |
| `DJANGO_DEBUG` | `0`; attivare soltanto per diagnostica locale |
| `DJANGO_ALLOWED_HOSTS` | Host locali consentiti |
| `DOCUMENT_AI_DATA_DIR` | `.data` nella cartella del progetto; usare `/var/lib/document-ai` nei servizi di esempio |
| `DOCUMENT_AI_ENDPOINT` | `http://127.0.0.1:8081/v1` |
| `DOCUMENT_AI_MODEL` | `local`, coerente con `--alias local` nel runtime |
| `DOCUMENT_AI_TIMEOUT` | `180`, secondi per la singola chiamata AI |
| `DOCUMENT_AI_CONTEXT_CHARS` | `6500`, dimensione iniziale delle porzioni di testo |
| `DOCUMENT_AI_MAX_TOKENS` | `1200`, limite della risposta generata |
| `DOCUMENT_AI_OCR_LANGUAGE` | `ita+eng` |
| `DOCUMENT_AI_MAX_UPLOAD_MB` | `20` |
| `DOCUMENT_AI_MAX_PAGES` | `50`, limite per i PDF |
| `DOCUMENT_AI_MAX_CHARS` | `250000`, limite del testo elaborabile |

Cambiare il budget in caratteri non equivale a cambiare il contesto in token: anche istruzioni, descrizioni dei campi e risposta occupano contesto. Mantenere spazio per tutti questi elementi. Un documento lungo comporta più chiamate, senza aumentare la parallelizzazione.

## Dati e uso locale

Il servizio iniziale è pensato per un utente sul proprio computer e ascolta su `127.0.0.1`. Non espone autenticazione o separazione per clienti: non pubblicarlo su Internet e non estenderne l'accesso a una rete condivisa senza aggiungere quei controlli.

Gli originali restano conservati fino all'eliminazione esplicita. Il database contiene anche testo estratto, risultati e revisioni: rimuovere soltanto il file originale non elimina le sue informazioni derivate. I backup sono copie ulteriori da gestire separatamente. Modelli, dati locali, database e `.env` non fanno parte del codice da inviare a Git.

L'app non chiama servizi AI remoti; l'endpoint di inferenza accetta soltanto indirizzi locali. Download di dipendenze e modello avvengono durante il setup esplicito. L'assenza di chiamate cloud durante il trattamento non rende i dati anonimi.

## Estensioni previste

Le funzioni di lettura e inferenza sono moduli di servizio separati dalle viste Django. Nuovi parser, template, runtime e formati di esportazione possono essere aggiunti senza introdurre subito un'architettura distribuita. Sintesi, mascheramento e consultazione conversazionale richiedono flussi e verifiche propri.
