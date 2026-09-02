from __future__ import annotations

import frappe


def _get_retry_limit() -> int:
    # Reusa o batch size como teto simples de tentativas por log.
    return frappe.db.get_single_value("FCM Settings", "batch_size") or 100


def retry_failed_notifications():
    """Reenvia notificacoes que falharam por erro temporario (nao token invalido)."""
    limit = _get_retry_limit()
    failed = frappe.get_all(
        "FCM Notification Log",
        filters={"status": "Failed", "retry_count": ["<", 3]},
        fields=["name", "title", "body", "token", "data_payload", "retry_count"],
        limit=limit,
    )
    if not failed:
        return

    from erpnext_notifications.firebase.client import _InvalidTokenError
    from erpnext_notifications.firebase.client import get_settings, send_to_token

    try:
        get_settings()
    except Exception:
        return  # nao configurado/desabilitado; nada a fazer

    for log in failed:
        data = _parse_payload(log.data_payload)
        try:
            res = send_to_token(log.token, log.title, body=log.body or "", data=data)
            _mark(log.name, "Sent", message_id=res.get("message_id"))
        except _InvalidTokenError as exc:
            _mark(log.name, "Failed", error=exc)
            _deactivate_token(log.token)
        except Exception as exc:
            _mark(log.name, "Failed", error=exc, increment=True)


def _parse_payload(raw):
    if not raw:
        return None
    try:
        import json

        return json.loads(raw)
    except Exception:
        return None


def _mark(log_name, status, message_id=None, error=None, increment=False):
    doc = frappe.get_doc("FCM Notification Log", log_name)
    doc.status = status
    if message_id:
        doc.fcm_message_id = message_id
    if error:
        doc.error_message = str(error)[:2000]
    if status in ("Sent", "Failed"):
        doc.send_time = frappe.utils.now_datetime()
    if increment:
        doc.retry_count = (doc.retry_count or 0) + 1
    doc.flags.ignore_permissions = True
    doc.save(ignore_permissions=True)


def _deactivate_token(token):
    device = frappe.db.get_value("FCM Device", {"token": token}, "name")
    if not device:
        return
    try:
        doc = frappe.get_doc("FCM Device", device)
        doc.deactivate(reason="Token invalido no reenvio FCM")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "FCM: desativacao de token")


def cleanup_old_logs():
    """Remove logs de notificacao mais antigos que o periodo de retencao."""
    days = frappe.db.get_single_value("FCM Settings", "retention_days") or 90
    cutoff = frappe.utils.add_days(frappe.utils.now_datetime(), -days)
    frappe.db.delete("FCM Notification Log", {"creation": ["<", cutoff]})


def cleanup_invalid_devices():
    """Marca como inativos dispositivos que acumulam erro de token invalido."""
    limit = _get_retry_limit()
    invalid = frappe.get_all(
        "FCM Device",
        filters={
            "is_active": 1,
            "last_error": ["like", "Token FCM invalido%"],
        },
        pluck="name",
        limit=limit,
    )
    for name in invalid:
        try:
            doc = frappe.get_doc("FCM Device", name)
            doc.deactivate(reason="Token invalido persistente")
        except Exception:
            frappe.log_error(frappe.get_traceback(), "FCM: limpeza de dispositivo")
