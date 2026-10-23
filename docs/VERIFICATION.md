# Verifiche della prima versione

Verifica del 23 ottobre 2026, su Linux con Python 3.12. La VM aziendale e il MacBook dell'utente non sono stati modificati né utilizzati durante queste prove.

- Installazione delle dipendenze fissate in un ambiente virtuale pulito: completata.
- `manage.py check` e controllo migrazioni: superati.
- `manage.py test tests`: **47 test superati**, senza scaricare modelli durante i test automatici.
- Fonti PDF/DOCX, ordine delle tabelle Word, casi mancanti, limiti, revisione, esportazioni e cancellazione: verificati con dati sintetici.
- OCR reale su PDF sintetico scansionato: verificato con Poppler e Tesseract in inglese. La qualità OCR italiana richiede una prova con i dati lingua `ita` e documenti rappresentativi.
- HTTP reale con Gunicorn e `DEBUG=0`: home, CSS e JavaScript restituiscono correttamente i contenuti.

## Richiesta reale al modello locale

È stato compilato llama.cpp alla revisione `f5027fb21307eb264aed483242603d68c87b0fe3`, con AVX attivo e AVX2/FMA/F16C/BMI2 disattivati. La compilazione dimostra che il profilo è praticabile nell'ambiente di verifica; non è una misura del processore o del carico VMware aziendale.

Modello: Qwen2.5-1.5B-Instruct Q4_K_M ufficiale, 1.117.320.736 byte, checksum SHA-256 verificato dallo script. La richiesta prodotta dal motore dell'app con schema JSON è stata accettata dal server.

Su un breve contratto sintetico italiano:

| Campo | Esito |
| --- | --- |
| Importo | `1200.0`, con citazione corretta |
| Durata | `12 mesi`, con citazione corretta |
| Parti | Il modello ha proposto i nomi corretti con una citazione estranea. L'app ha respinto il campo, restituendo `null` e un avviso. |

Due richieste, compresa una diagnostica, hanno confermato lo stesso limite. Questi risultati confermano l'integrazione e il funzionamento dei controlli sulle fonti; non certificano accuratezza su documenti legali. Una citazione esistente e contenente il valore non prova da sola che il valore risponda correttamente alla domanda del template.

Non sono stati eseguiti benchmark sulla VM aziendale né prove di carico multiutente. Prima dell'uso operativo occorre confrontare estrazioni, omissioni e riferimenti con un campione annotato manualmente, separando testo digitale, scansioni e tabelle.
