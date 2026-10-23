# Trasferimento a Ubuntu 22.04 e systemd

Queste sono istruzioni di preparazione e unità di esempio. Non installano né modificano i servizi presenti sul server.

La VM osservata espone 4 vCPU Xeon E5-2680, AVX ma non AVX2, FMA o F16C, circa 16 GB di RAM e 74 GB disponibili nella partizione principale. Il breve campione quasi inattivo non descrive i picchi. Prima di destinare risorse al pilota, misurare carico abituale e impatto sulle applicazioni Django e sul database esistenti.

## Dipendenze

```bash
sudo apt-get update
sudo apt-get install python3-venv python3-pip build-essential cmake git libssl-dev \
  poppler-utils tesseract-ocr tesseract-ocr-ita tesseract-ocr-eng
```

Preparare la directory del progetto e il suo ambiente virtuale; installare `requirements.txt`. Eseguire le migrazioni e `seed_templates` con la stessa configurazione dati utilizzata dai servizi, quindi `python manage.py collectstatic --noinput` prima di attivare la protezione del percorso codice in systemd. WhiteNoise serve gli asset raccolti anche con `DJANGO_DEBUG=0`. Nessun documento aziendale deve entrare nella repository.

## Runtime compatibile con AVX

Un binario compilato per un processore moderno può contenere istruzioni non disponibili nella VM. Compilare `llama.cpp` sulla destinazione con un profilo esplicito. Esempio riferito alle opzioni upstream verificate il 23 ottobre 2026:

```bash
git clone https://github.com/ggml-org/llama.cpp.git /opt/llama.cpp
cd /opt/llama.cpp
git checkout b11829
cmake -S . -B build-avx \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_NATIVE=OFF \
  -DGGML_SSE42=ON \
  -DGGML_AVX=ON \
  -DGGML_AVX2=OFF \
  -DGGML_FMA=OFF \
  -DGGML_F16C=OFF \
  -DGGML_BMI2=OFF \
  -DGGML_AVX_VNNI=OFF \
  -DGGML_AVX512=OFF \
  -DGGML_CPU_ALL_VARIANTS=OFF \
  -DGGML_BLAS=OFF \
  -DGGML_LLAMAFILE=OFF \
  -DLLAMA_CURL=OFF
cmake --build build-avx --config Release --target llama-server -j 2
```

Il tag rende ripetibile il riferimento; valutare gli aggiornamenti upstream prima di un utilizzo stabile. Questa compilazione non è stata eseguita sulla vostra VM. La verifica finale è l'avvio del server con il modello e una richiesta reale. Se `llama.cpp` cambia opzioni o nomi dei target, consultare la [guida build](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md) della revisione scelta.

Scaricare il modello con `python scripts/download_model.py` dalla directory di document-ai. L'avvio manuale equivalente al profilo CPU è:

```bash
/opt/llama.cpp/build-avx/bin/llama-server \
  --model /opt/document-ai/models/qwen2.5-1.5b-instruct-q4_k_m.gguf \
  --alias local --host 127.0.0.1 --port 8081 \
  --threads 2 --threads-batch 2 --ctx-size 8192 --parallel 1 --n-gpu-layers 0
```

## Percorsi delle unità di esempio

| Risorsa | Percorso / account |
|---|---|
| Sorgenti e ambiente | `/opt/document-ai`, `/opt/document-ai/.venv` |
| Runtime | `/opt/llama.cpp/build-avx/bin/llama-server` |
| Dati scrivibili | `/var/lib/document-ai` |
| Configurazione | `/etc/document-ai.env` |
| Utente di servizio | `documentai`, con accesso ai dati e lettura del codice/modello |

Creare l'account e i percorsi con permessi adeguati prima di installare le unità. Copiare `.env.example` in `/etc/document-ai.env`, impostare almeno:

```dotenv
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_SECRET_KEY=sostituire-con-una-chiave-casuale-propria
DOCUMENT_AI_DATA_DIR=/var/lib/document-ai
DOCUMENT_AI_ENDPOINT=http://127.0.0.1:8081/v1
DOCUMENT_AI_MODEL=local
```

Il file contiene configurazione riservata: consentire la lettura soltanto agli amministratori e all'account del servizio. Non copiarlo su Git. Il worker necessita di Poppler, Tesseract e relativi dati lingua nel percorso di sistema.

I file in `deploy/` definiscono:

- `document-ai-web.service`: Gunicorn con un worker e due thread, ascolto solo locale;
- `document-ai-worker.service`: worker della coda;
- `document-ai-model.service`: processo persistente del modello;
- `document-ai.slice`: budget aggregato per tutti e tre.

Il budget iniziale è `CPUQuota=200%`, `MemoryHigh=5G`, `MemoryMax=6G`. La quota equivale al tempo di due CPU, non riserva due core. `MemoryHigh` può rallentare i processi; il superamento non contenibile di `MemoryMax` può terminarli. Sono valori di partenza da provare, non consumi garantiti né una garanzia di assenza di impatto. Controllare la gerarchia cgroup e l'applicazione effettiva dei limiti.

Una volta adattati account, percorsi e configurazione, le unità possono essere copiate in `/etc/systemd/system/`. Eseguire le migrazioni prima di avviare web e worker. Le azioni amministrative successive sono:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now document-ai-model document-ai-worker document-ai-web
sudo systemctl status document-ai-model document-ai-worker document-ai-web
sudo journalctl -u document-ai-worker -n 50 --no-pager
```

L'ordine di avvio non assicura che il modello abbia già completato il caricamento: attendere che sia pronto prima di inviare il primo documento. Un'elaborazione fallita va controllata e riprovata dall'app.

Per un accesso personale dal MacBook mantenendo l'app sul loopback della VM, si può utilizzare un tunnel SSH autorizzato:

```bash
ssh -L 8000:127.0.0.1:8000 utente@server
```

Aprire poi `http://127.0.0.1:8000` sul MacBook. L'accesso condiviso a più utenti richiede autenticazione, autorizzazioni e una configurazione di pubblicazione dedicata.

## Prima valutazione sulla VM

Usare documenti sintetici o un campione approvato internamente, controllando valori e fonti. Misurare tempo totale, numero di porzioni elaborate, memoria disponibile, swap e latenza dei servizi esistenti, prima e durante il lavoro. Elaborare scansioni, tabelle e documenti lunghi come casi separati. Aumentare il budget soltanto in base a quelle misure.

Riferimenti: [controllo risorse systemd 249](https://www.freedesktop.org/software/systemd/man/249/systemd.resource-control.html), [opzioni CPU ggml](https://github.com/ggml-org/llama.cpp/blob/master/ggml/CMakeLists.txt), [server llama.cpp](https://github.com/ggml-org/llama.cpp/tree/master/tools/server).
