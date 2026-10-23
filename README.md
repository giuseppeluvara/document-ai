# document-ai

App locale per estrarre dati strutturati da documenti usando template personalizzabili e un piccolo modello AI in CPU. Prima destinazione: MacBook; configurazione di trasferimento per Ubuntu 22.04 su VM con 4 vCPU e 16 GB di RAM.

## Cosa fa la prima versione

- Importa PDF testuali, PDF scansionati stampati e Word `.docx`.
- Estrae testo e tabelle Word; per i PDF tenta di preservare la disposizione del testo. Esegue OCR soltanto sulle pagine che ne hanno bisogno.
- Applica template con campi, descrizioni e tipi configurabili, ad esempio parti, oggetto, importo, durata e scadenze.
- Mostra valori e citazioni del documento, segnala dati mancanti e permette la revisione.
- Esporta JSON e XLSX; conserva gli originali e i risultati fino alla loro eliminazione dall'app.

Le elaborazioni sono in coda, una alla volta. L'app web non carica il modello nei processi Django. Dopo il download iniziale di software, lingue OCR e modello, l'elaborazione non richiede servizi AI esterni.

## Avvio sul MacBook

Servono Python 3.10 o successivo, Homebrew e circa 2 GB di spazio aggiuntivo per il modello e i suoi file temporanei, oltre a dipendenze e documenti.

Se usi l'archivio ZIP, estrailo e apri la cartella `document-ai`: salta il comando `git clone` qui sotto. La pubblicazione su GitHub è un passaggio separato dall'avvio locale.

```bash
brew install python tesseract tesseract-lang poppler llama.cpp
git clone https://github.com/giuseppeluvara/document-ai.git
cd document-ai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_templates
python manage.py collectstatic --noinput
```

Controllare che `tesseract --list-langs` includa `ita` ed `eng`. Il profilo predefinito usa queste due lingue.

Scaricare esplicitamente il modello iniziale, **Qwen2.5-1.5B-Instruct Q4_K_M** (circa 1,12 GB; Apache 2.0):

```bash
python scripts/download_model.py
bash scripts/start_model.sh
```

Lo script controlla il checksum SHA-256 pubblicato nella repository ufficiale Qwen prima di rendere utilizzabile il file. Il modello rimane in `models/`, escluso da Git. Attendere che `llama-server` abbia terminato il caricamento.

In un **secondo terminale**, dalla cartella del progetto:

```bash
source .venv/bin/activate
python manage.py runworker
```

In un **terzo terminale**:

```bash
source .venv/bin/activate
python manage.py runserver 127.0.0.1:8000
```

Aprire <http://127.0.0.1:8000>. L'app iniziale è locale e monoutente. Usare un template di esempio o crearne uno, caricare un documento e attendere il risultato. Se il modello non è disponibile, l'elaborazione restituisce un errore esplicito; non sostituisce l'AI con dati simulati.

## Configurazione e limiti

Le impostazioni sono in `.env.example`: endpoint locale `http://127.0.0.1:8081/v1`, modello `local`, OCR `ita+eng`, caricamenti fino a 20 MB e documenti fino a 50 pagine PDF. [Configurazione e architettura](docs/ARCHITECTURE.md) descrive formato dei template, coda e conservazione. Per il server aziendale seguire [Ubuntu e systemd](docs/LINUX.md).

- `.doc` legacy e scrittura a mano non sono supportati; convertire Word in `.docx`.
- Le immagini incorporate nei DOCX non vengono sottoposte a OCR: esportare quel documento come PDF se contiene pagine scansionate.
- Note, caselle di testo, revisioni e oggetti incorporati Word non sono acquisiti integralmente: l'app segnala queste strutture e consiglia di esportare una versione PDF consolidata.
- Le tabelle sono materiale da cui estrarre campi. Non è garantita la ricostruzione di ogni griglia PDF o tabella complessa.
- Word non ha pagine stabili: le fonti indicano blocchi e tabelle, anziché inventare numeri di pagina.
- Una citazione verificata dimostra che il passaggio esiste, non che l'interpretazione del modello sia corretta. Controllare risultati, omissioni e conflitti prima dell'uso.
- Sintesi, anonimizzazione e chatbot sono sviluppi successivi.
- Il profilo CPU usa due thread, un solo slot e contesto di 8.192 token. I tempi effettivi sulla VM AVX richiedono una prova; quelli del MacBook non costituiscono una stima per il server.

## Verifica

```bash
python -m pip install -r requirements-dev.txt
python manage.py check
python manage.py test tests
```

I test automatici usano documenti sintetici e risposte AI controllate, senza scaricare un modello. Per valutare il modello reale, provare un campione di documenti rappresentativo e confrontare valori, fonti, campi mancanti, tempo e memoria con un risultato annotato manualmente.

La [verifica iniziale](docs/VERIFICATION.md) riporta i 47 test superati e la prova reale con Qwen: due campi corretti e un campo respinto per una citazione sbagliata.

## Fonti tecniche

[Django 5.2](https://docs.djangoproject.com/en/5.2/) · [llama.cpp server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server) · [Modello Qwen ufficiale](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF) · [pypdf](https://pypdf.readthedocs.io/en/stable/user/extract-text.html) · [python-docx](https://python-docx.readthedocs.io/) · [Tesseract](https://tesseract-ocr.github.io/)
