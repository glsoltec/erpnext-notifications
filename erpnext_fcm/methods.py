from __future__ import annotations

import json

import frappe
from frappe import _

from erpnext_fcm import services


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
            _dispatch_rule(doc, rule)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"FCM: falha ao processar regra {doc.doctype}.{method}",
            )


def _dispatch_rule(doc, rule):
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