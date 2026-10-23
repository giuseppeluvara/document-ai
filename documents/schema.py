import re
from django.core.exceptions import ValidationError

FIELD_TYPES = {'text', 'number', 'date', 'list'}

def validate_fields(fields):
    if not isinstance(fields, list) or not 1 <= len(fields) <= 12:
        raise ValidationError('Definisci da 1 a 12 campi per template.')
    keys = set()
    cleaned = []
    for field in fields:
        if not isinstance(field, dict):
            raise ValidationError('Ogni campo deve essere un oggetto JSON.')
        key = field.get('key', '')
        label = field.get('label', '')
        description = field.get('description', '')
        kind = field.get('type', 'text')
        if not isinstance(key, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,63}', key):
            raise ValidationError('La chiave deve iniziare con una lettera minuscola e contenere solo lettere, numeri e underscore (max 64).')
        if key in keys:
            raise ValidationError('Le chiavi dei campi devono essere uniche.')
        if not isinstance(label, str) or not label.strip() or len(label) > 80:
            raise ValidationError('Ogni campo richiede un nome, fino a 80 caratteri.')
        if not isinstance(description, str) or len(description) > 240:
            raise ValidationError('La descrizione di ciascun campo può avere fino a 240 caratteri.')
        if not isinstance(kind, str) or kind not in FIELD_TYPES:
            raise ValidationError('Tipo campo non valido: usa text, number, date o list.')
        keys.add(key)
        cleaned.append({'key': key, 'label': label.strip(), 'description': description.strip(), 'type': kind})
    return cleaned
