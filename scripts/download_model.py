#!/usr/bin/env python3
"""Download the explicitly selected public GGUF and verify its published SHA-256."""

import argparse
import hashlib
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request


FILENAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
URL = f"https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/{FILENAME}"
# Published by the official Qwen repository; checked 2026-10-23.
# https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/blob/main/qwen2.5-1.5b-instruct-q4_k_m.gguf
SHA256 = "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(
        description="Scarica Qwen2.5-1.5B-Instruct Q4_K_M (circa 1,12 GB), licenza Apache 2.0."
    )
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parents[1] / "models")
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    destination = args.directory / FILENAME
    if destination.exists():
        if file_hash(destination) == SHA256:
            print(f"Modello già presente e verificato: {destination}")
            return 0
        print(f"File esistente con checksum diverso: {destination}. Spostarlo prima di riprovare.", file=sys.stderr)
        return 1
    temporary = destination.with_suffix(destination.suffix + ".part")
    print(f"Download esplicito da Qwen/Hugging Face: {FILENAME} (circa 1,12 GB)", flush=True)
    try:
        request = urllib.request.Request(URL, headers={"User-Agent": "document-ai-model-setup/1.0"})
        digest = hashlib.sha256()
        written = 0
        with urllib.request.urlopen(request, timeout=90) as source, temporary.open("wb") as target:
            while True:
                block = source.read(1024 * 1024)
                if not block:
                    break
                written += len(block)
                if written > 2_000_000_000:
                    raise ValueError("Dimensione inattesa del download.")
                digest.update(block)
                target.write(block)
            target.flush()
            os.fsync(target.fileno())
        if digest.hexdigest() != SHA256:
            raise ValueError("Checksum SHA-256 diverso da quello verificato: il file non sarà utilizzato.")
        temporary.replace(destination)
    except (OSError, urllib.error.URLError, ValueError) as exc:
        temporary.unlink(missing_ok=True)
        print(f"Download non completato: {exc}", file=sys.stderr)
        return 1
    print(f"Modello verificato: {destination}")
    print(f"SHA-256: {SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
