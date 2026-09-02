from __future__ import annotations

import json
from typing import Any

import frappe

from erpnext_notifications.firebase.client import (
    _InvalidTokenError,
    get_settings,
    send_to_token,
)


def get_active_tokens_for_user(user: str) -> list[str]:
    if not user:
        return []
    return frappe.get_all(
        "FCM Device",
        filters={"user": user, "is_active": 1},
        pluck="token",
        ignore_permissions=True,
    )


def _get_device_user(token: str) -> str | None:
    """Retorna o usuario dono do dispositivo (para logar um log por token)."""
    return frappe.db.get_value("FCM Device", {"token": token}, "user")


def _auto_remove_invalid() -> bool:
    try:
        return bool(frappe.get_cached_doc("FCM Settings").get("auto_remove_invalid"))
    except Exception:
        return True  # comportamento seguro por padrao


def _create_log(title, body, data, user=None, token=None, status="Queued"):
    settings = frappe.get_cached_doc("FCM Settings")
    if not settings.log_enabled:
        return None
    log = frappe.new_doc("FCM Notification Log")
    log.title = title
    log.body = body or ""
    log.user = user
    log.token = token
    if data:
        log.data_payload = json.dumps(data, ensure_ascii=False)
    log.status = status
    log.retryable = 1
    log.flags.ignore_permissions = True
    log.insert(ignore_permissions=True)
    return log


def _update_log(log, status, message_id=None, error=None, retryable=None):
    if not log:
        return
    log.status = status
    if message_id:
        log.fcm_message_id = message_id
    if error:
        log.error_message = str(error)[:2000]
    if status in ("Sent", "Failed", "Invalid Token"):
        log.send_time = frappe.utils.now_datetime()
    if retryable is not None:
        log.retryable = 1 if retryable else 0
    log.flags.ignore_permissions = True
    log.save(ignore_permissions=True)


def _deactivate_token(token: str, reason: str = "Token invalido no envio FCM"):
    """Desativa o token se 'auto_remove_invalid' estiver habilitado."""
    if not _auto_remove_invalid():
        return
    device = frappe.db.get_value("FCM Device", {"token": token}, "name")
    if not device:
        return
    try:
        doc = frappe.get_doc("FCM Device", device)
        doc.deactivate(reason=reason)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "FCM: desativacao de token")


def send_to_user(
    user: str,
    title: str,
    body: str = "",
    data: dict | None = None,
    image: str | None = None,
    enqueue: bool = False,
) -> dict:
    """Envia notificacao para todos os dispositivos ativos de um usuario."""
    tokens = get_active_tokens_for_user(user)
    if not tokens:
        return {"user": user, "tokens": 0, "sent": 0, "failed": 0, "results": []}
    return _send_to_tokens(tokens, title, body, data=data, image=image, user=user, enqueue=enqueue)


def send_to_users(
    users: list[str],
    title: str,
    body: str = "",
    data: dict | None = None,
    image: str | None = None,
    enqueue: bool = False,
) -> dict:
    """Envia para uma lista de usuarios.

    Gera um log por token (o usuario real do dispositivo e resolvido por token),
    evitando valor invalido no campo Link 'user' para envios multi-usuario.
    """
    tokens = []
    for user in users:
        tokens.extend(get_active_tokens_for_user(user))
    return _send_to_tokens(tokens, title, body, data=data, image=image, enqueue=enqueue)


def send_to_all(
    title: str,
    body: str = "",
    data: dict | None = None,
    image: str | None = None,
    enqueue: bool = False,
) -> dict:
    """Envia para todos os dispositivos ativos do sistema."""
    tokens = frappe.get_all(
        "FCM Device", filters={"is_active": 1}, pluck="token", ignore_permissions=True
    )
    return _send_to_tokens(tokens, title, body, data=data, image=image, enqueue=enqueue)


def _send_to_tokens(
    tokens: list[str],
    title: str,
    body: str,
    data: dict | None,
    image: str | None,
    user: str | None = None,
    enqueue: bool = False,
) -> dict:
    if enqueue:
        frappe.enqueue(
            "erpnext_notifications.services._send_tokens_job",
            tokens=tokens,
            title=title,
            body=body,
            data=data,
            image=image,
            user=user,
            queue="short",
        )
        return {"queued": len(tokens)}

    return _send_tokens_job(tokens, title, body, data=data, image=image, user=user)


def _send_tokens_job(
    tokens: list[str],
    title: str,
    body: str,
    data: dict | None,
    image: str | None,
    user: str | None = None,
) -> dict:
    get_settings()  # valida que esta habilitado
    results = []
    sent = failed = 0
    for token in tokens:
        if not token:
            continue
        log = None
        device_user = _get_device_user(token) or user
        try:
            log = _create_log(title, body, data, user=device_user, token=token)
            res = send_to_token(token, title, body=body, data=data, image=image)
            sent += 1
            _update_log(log, "Sent", message_id=res.get("message_id"), retryable=False)
            results.append({"token": token, "ok": True})
        except _InvalidTokenError as exc:
            failed += 1
            _deactivate_token(token)
            _update_log(log, "Invalid Token", error=exc, retryable=False)
            results.append({"token": token, "ok": False, "error": str(exc)})
        except Exception as exc:
            failed += 1
            _update_log(log, "Failed", error=exc, retryable=True)
            results.append({"token": token, "ok": False, "error": str(exc)})
    return {"tokens": len(tokens), "sent": sent, "failed": failed, "results": results}


def send_raw_tokens(
    tokens: list[str],
    title: str,
    body: str,
    data: dict | None,
    image: str | None,
) -> dict:
    """Envia para tokens arbitrarios (sem vincular a usuario/log). Usado pela API direta."""
    return _send_tokens_job(tokens, title, body, data=data, image=image)