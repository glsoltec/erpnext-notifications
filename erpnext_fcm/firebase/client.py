from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _

try:
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account
except ImportError:  # pragma: no cover
    frappe.log_error(_("Dependencia 'google-auth' nao instalada. Rode: pip install google-auth"))
    raise

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
TOKEN_URI = "https://oauth2.googleapis.com/token"
FCM_SEND_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"

# Erros que indicam token invalido / dispositivo removido
TOKEN_ERROR_CODES = {
    "UNREGISTERED",
    "INVALID_ARGUMENT",
    "NOT_FOUND",
    "SENDER_ID_MISMATCH",
    "MISMATCH_SENDER_ID",
}


def get_settings() -> "frappe.model.document.Document":
    settings = frappe.get_cached_doc("FCM Settings")
    if not settings.enabled:
        frappe.throw(_("Notificacoes FCM estao desabilitadas em FCM Settings."))
    return settings


def get_service_account() -> dict:
    settings = frappe.get_cached_doc("FCM Settings")
    raw = settings.get("service_account_json")
    if not raw:
        frappe.throw(_("Service account nao configurado em FCM Settings."))
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        frappe.throw(_("service_account_json em FCM Settings nao e um JSON valido."))
    return {}


def get_project_id() -> str:
    settings = frappe.get_cached_doc("FCM Settings")
    if settings.get("project_id"):
        return settings.project_id
    return get_service_account().get("project_id", "")


def get_session() -> AuthorizedSession:
    """Sessao autorizada OAuth2. Renova o token automaticamente quando expira."""
    credentials = service_account.Credentials.from_service_account_info(
        get_service_account(),
        scopes=[FCM_SCOPE],
    )
    return AuthorizedSession(credentials)


def render_payload(
    token: str,
    title: str,
    body: str = "",
    data: dict | None = None,
    image: str | None = None,
) -> dict:
    """Monta o payload HTTP v1 do FCM para um unico token."""
    notification: dict[str, Any] = {"title": title}
    if body:
        notification["body"] = body
    if image:
        notification["image"] = image

    message: dict[str, Any] = {
        "token": token,
        "notification": notification,
        "android": {"priority": "HIGH"},
        "apns": {"payload": {"aps": {"sound": "default"}}},
    }
    if data:
        message["data"] = {str(k): str(v) for k, v in data.items()}
    return {"message": message}


def _parse_error_details(resp) -> tuple[str, str]:
    """Extrai (error_code, message) do corpo de erro do FCM."""
    error_code = ""
    message = ""
    try:
        payload = resp.json()
        error = payload.get("error", {})
        error_code = error.get("status", "")
        message = error.get("message", "")
    except Exception:
        message = resp.text
    return error_code, message


def send_to_token(
    token: str,
    title: str,
    body: str = "",
    data: dict | None = None,
    image: str | None = None,
) -> dict:
    """Envia uma notificacao para um unico token. Retorna {'message_id': ...} ou levanta excecao."""
    session = get_session()
    project_id = get_project_id()
    if not project_id:
        frappe.throw(_("project_id do Firebase nao encontrado em FCM Settings."))

    url = FCM_SEND_URL.format(project_id=project_id)
    payload = render_payload(token, title, body=body, data=data, image=image)
    resp = session.post(url, json=payload, timeout=30)

    if resp.status_code == 200:
        msg = resp.json().get("name", "")
        return {"message_id": msg}

    error_code, message = _parse_error_details(resp)
    error = RuntimeError(f"FCM HTTP {resp.status_code}: {error_code} {message}".strip())

    if error_code in TOKEN_ERROR_CODES:
        error = _InvalidTokenError(error_code, message, token)
    raise error


class _InvalidTokenError(RuntimeError):
    """Indica token invalido; o dispositivo deve ser desativado."""

    def __init__(self, code: str, message: str, token: str):
        super().__init__(f"Token FCM invalido ({code}): {message}")
        self.code = code
        self.token = token


def send_to_tokens(
    tokens: list[str],
    title: str,
    body: str = "",
    data: dict | None = None,
    image: str | None = None,
    invalid_token_callback=None,
) -> dict:
    """Envia para varios tokens. Retorna {'sent': n, 'failed': n, 'results': [...]}.

    `invalid_token_callback` (opcional) recebe o token invalido para desativacao.
    """
    results = []
    sent = failed = 0
    for token in tokens:
        if not token:
            continue
        try:
            res = send_to_token(token, title, body=body, data=data, image=image)
            sent += 1
            results.append({"token": token, "ok": True, **res})
        except _InvalidTokenError as exc:
            failed += 1
            results.append({"token": token, "ok": False, "error": str(exc)})
            if invalid_token_callback:
                invalid_token_callback(exc.token)
        except Exception as exc:  # nao deixa um token derrubar o lote
            failed += 1
            results.append({"token": token, "ok": False, "error": str(exc)})
    return {"sent": sent, "failed": failed, "results": results}
