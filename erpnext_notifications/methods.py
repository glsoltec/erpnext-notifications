from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import get_url, strip_html

from erpnext_notifications import services
from erpnext_notifications.validation import safe_notification_url

IDEMPOTENCY_TTL = 60  # segundos; evita envio duplicado do mesmo evento no mesmo documento


def _idempotency_key(doc, method: str, rule_name: str) -> str:
    return f"fcm:idem:{doc.doctype}:{doc.name}:{method}:{rule_name}"


def _mark_dispatched(key: str) -> bool:
    """Retorna True se o evento ja foi processado recentemente (e marca novo)."""
    if frappe.local.flags.get(key):
        return True
    if frappe.cache.get(key):
        return True
    frappe.local.flags[key] = True
    frappe.cache.set(key, True, expires_in_sec=IDEMPOTENCY_TTL)
    return False


def send_notification_log_push(doc, method=None):
    """Relay das notificacoes nativas do ERPNext (Notification Log) para push.

    Registrado em hooks.py em doc_events['Notification Log']['after_insert'].
    O `for_user` recebe a notificacao em todos os seus dispositivos ativos (Web e mobile).
    """
    settings = frappe.get_cached_doc("FCM Settings")
    if not settings.enabled or not settings.enable_fcm:
        return
    if not doc.for_user:
        return

    title = _notification_title(doc)
    body = strip_html(doc.subject or "")[:200]
    data = {"type": doc.type or "", "subject": body}
    if doc.link:
        url = safe_notification_url(get_url(doc.link))
        if url:
            data["click_action"] = url

    try:
        services.send_to_user(doc.for_user, title, body=body, data=data, enqueue=True)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "FCM: relay de Notification Log")


def _notification_title(doc) -> str:
    titles = {
        "Mention": _("New Mention"),
        "Assignment": _("Assignment Update"),
        "Share": _("Document Shared With You"),
        "Energy Point": _("Energy Point Update"),
        "Alert": _("Alert"),
    }
    return titles.get(doc.type) or _("New Notification")


def handle_doc_event(doc, method: str):
    """Gatilho geral de eventos de documento.

    Registrado em hooks.py para varios DocTypes. A selecao real (quem, quando e o
    conteudo) e feita pelas regras configuradas em FCM Settings > Notification Rules.
    """
    settings = frappe.get_cached_doc("FCM Settings")
    if not settings.enabled:
        return

    rules = [
        r
        for r in settings.notification_rules
        if r.enabled and r.doctype == doc.doctype and r.event == method
    ]
    if not rules:
        return

    for rule in rules:
        try:
            _dispatch_rule(doc, rule, method)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"FCM: falha ao processar regra {doc.doctype}.{method}",
            )


def _dispatch_rule(doc, rule, method: str):
    key = _idempotency_key(doc, method, rule.name)
    if _mark_dispatched(key):
        return

    recipient = _resolve_recipient(doc, rule.recipient_field)
    if not recipient:
        return

    context = {"doc": doc, "recipient": recipient}
    title = _render(rule.title_template, context) or (
        frappe.get_cached_doc("FCM Settings").get("default_title") or _("Notificacao")
    )
    body = _render(rule.body_template, context)
    data = _render_data(rule.data_template, context)

    services.send_to_user(recipient, title, body=body, data=data, enqueue=True)


def _resolve_recipient(doc, recipient_field: str) -> str | None:
    if recipient_field:
        value = doc.get(recipient_field)
        if value:
            return value
    return doc.get("owner")


def _render(template: str, context: dict) -> str:
    if not template:
        return ""
    return frappe.render_template(template, context)


def _render_data(template: str, context: dict) -> dict:
    if not template:
        return {}
    try:
        raw = frappe.render_template(template, context)
        parsed = json.loads(raw or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "FCM: data_template invalido")
        return {}