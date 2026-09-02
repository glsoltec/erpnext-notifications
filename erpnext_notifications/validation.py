from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

# Limites de payload (defesa contra payloads excessivos e payload invalido p/ FCM)
MAX_TITLE_LEN = 120
MAX_BODY_LEN = 4000
MAX_IMAGE_URL_LEN = 2048
MAX_DATA_KEYS = 20
MAX_DATA_KEY_LEN = 200
MAX_DATA_VALUE_LEN = 500
MAX_RECIPIENTS = 500
MAX_RETRIES = 3

# Backoff exponencial (em segundos) por tentativa acumulada.
# 1a falha -> 60s | 2a -> 300s | 3a -> 1800s | demais -> 1800s
RETRY_BACKOFF = (60, 300, 1800)

# Codigos HTTP de erro transitario no FCM (reprocessaveis)
TRANSIENT_HTTP_CODES = {429, 500, 502, 503, 504}

_URL_SCHEMES_ALLOWED = {"https"}


def mask_token(token: str | None) -> str:
    """Mascara o token, exibindo apenas um sufixo curto.

    Tokens FCM sao identificadores sensiveis de dispositivo; nao devem ser
    expostos completos em listagens/UI.
    """
    if not token:
        return ""
    if len(token) <= 12:
        return "…"
    return f"…{token[-8:]}"


def _validate_token_format(token: str) -> str:
    token = (token or "").strip()
    if not token:
        raise ValueError("Token FCM e obrigatorio.")
    if len(token) > 2048 or any(char.isspace() or ord(char) < 32 for char in token):
        raise ValueError("Token FCM em formato invalido.")
    return token


def validate_payload(
    title: str,
    body: str,
    image: str | None = None,
    data: dict | None = None,
) -> dict:
    """Valida e normaliza o payload de notificacao.

    Levanta ValueError em payload invalido ou excessivo. Retorna um dict
    normalizado com 'title', 'body', 'image' e 'data'.
    """
    title = (title or "").strip()
    if not title:
        raise ValueError("Titulo da notificacao e obrigatorio.")
    if len(title) > MAX_TITLE_LEN:
        raise ValueError(f"Titulo excede {MAX_TITLE_LEN} caracteres.")

    body = (body or "").strip()
    if len(body) > MAX_BODY_LEN:
        raise ValueError(f"Corpo excede {MAX_BODY_LEN} caracteres.")

    image_out = None
    if image:
        image = image.strip()
        if len(image) > MAX_IMAGE_URL_LEN:
            raise ValueError("URL de imagem excede o limite.")
        image_out = safe_notification_url(image) or None

    data_out: dict = {}
    if data is not None:
        if not isinstance(data, dict):
            raise ValueError("Payload 'data' deve ser um objeto JSON.")
        if len(data) > MAX_DATA_KEYS:
            raise ValueError(f"Payload 'data' excede {MAX_DATA_KEYS} chaves.")
        for key, value in data.items():
            key = str(key).strip()
            if not key or len(key) > MAX_DATA_KEY_LEN:
                raise ValueError("Chave de 'data' invalida.")
            if isinstance(value, (dict, list)):
                raise ValueError("Payload 'data' nao pode conter objetos aninhados.")
            text = str(value)
            if len(text) > MAX_DATA_VALUE_LEN:
                raise ValueError(f"Valor de 'data' excede {MAX_DATA_VALUE_LEN} caracteres.")
            data_out[key] = text

    return {"title": title, "body": body, "image": image_out, "data": data_out}


def safe_notification_url(url: str | None) -> str | None:
    """Aceita somente URL https ou caminho relativo do proprio dominio.

    Bloqueia http, javascript:, data: e hosts externos nao autorizados.
    """
    if not url:
        return None
    url = url.strip()
    if url.startswith("/"):
        return url
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if parsed.scheme in _URL_SCHEMES_ALLOWED and parsed.netloc:
        return url
    return None


def normalize_recipients(recipients) -> list[str]:
    """Normaliza uma lista de destinatarios (strings de usuario).

    Aceita "*" (todos), uma string unica ou uma lista. Retorna lista limpa.
    """
    if recipients in ("*", "all"):
        return ["*"]
    if isinstance(recipients, str):
        recipients = [recipients]
    if not isinstance(recipients, (list, tuple)):
        raise ValueError("Destinatarios invalidos.")
    users = [u.strip() for u in recipients if isinstance(u, str) and u.strip()]
    if not users:
        raise ValueError("Nenhum destinatario informado.")
    if len(users) > MAX_RECIPIENTS:
        raise ValueError(f"Numero de destinatarios excede {MAX_RECIPIENTS}.")
    return users


def next_retry_at(attempt_count: int, now: datetime | None = None) -> datetime:
    """Calcula o proximo horario de retry com backoff exponencial."""
    now = now or datetime.now(timezone.utc)
    delay = RETRY_BACKOFF[min(max(attempt_count - 1, 0), len(RETRY_BACKOFF) - 1)]
    return now + timedelta(seconds=delay)


def is_transient_error(status_code: int | None) -> bool:
    """Indica se um erro HTTP do FCM e reprocessavel."""
    return status_code in TRANSIENT_HTTP_CODES


def can_retry(retry_count: int | None, retryable: bool | None) -> bool:
    """Indica se um log ainda e elegivel para retry."""
    if retryable is False:
        return False
    return (retry_count or 0) < MAX_RETRIES
