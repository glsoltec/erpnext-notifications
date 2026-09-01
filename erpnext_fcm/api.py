from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from erpnext_fcm import services


# ---------------------------------------------------------------------------
# Registro / gerenciamento de dispositivos (chamado pelo app mobile / web)
# ---------------------------------------------------------------------------
@frappe.whitelist()
def register_device(
    token: str,
    device_type: str = "Android",
    app_version: str = "",
    user_agent: str = "",
) -> dict:
    """Registra o token FCM do dispositivo para o usuario logado.

    Chamado via: POST /api/method/erpnext_fcm.api.register_device
    """
    token = (token or "").strip()
    if not token:
        frappe.throw(_("Token FCM e obrigatorio."))
    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.throw(_("Autenticacao necessaria para registrar dispositivo."))

    current = frappe.db.get_value("FCM Device", {"token": token}, "name")
    if current:
        doc = frappe.get_doc("FCM Device", current)
        doc.flags.ignore_permissions = True
    else:
        doc = frappe.new_doc("FCM Device")
    doc.update(
        {
            "user": frappe.session.user,
            "token": token,
            "device_type": device_type or "Android",
            "app_version": app_version,
            "user_agent": user_agent,
            "is_active": 1,
            "last_seen": frappe.utils.now_datetime(),
        }
    )
    doc.save(ignore_permissions=True)
    return {"status": "registered", "device": doc.name, "user": doc.user}


@frappe.whitelist()
def unregister_device(token: str) -> dict:
    """Desativa o token do usuario logado (logout / token rotacionado)."""
    token = (token or "").strip()
    current = frappe.db.get_value(
        "FCM Device",
        {"token": token, "user": frappe.session.user},
        "name",
    )
    if current:
        doc = frappe.get_doc("FCM Device", current)
        doc.flags.ignore_permissions = True
        doc.is_active = 0
        doc.save(ignore_permissions=True)
    return {"status": "unregistered"}


@frappe.whitelist()
def get_my_devices() -> list[dict[str, Any]]:
    """Lista os dispositivos ativos do usuario logado."""
    return frappe.get_all(
        "FCM Device",
        filters={"user": frappe.session.user, "is_active": 1},
        fields=["name", "token", "device_type", "app_version", "last_seen"],
    )


# ---------------------------------------------------------------------------
# Envio de notificacoes
# ---------------------------------------------------------------------------
@frappe.whitelist()
def send_notification(
    recipients: Any = None,
    title: str = "",
    body: str = "",
    data: dict | None = None,
    image: str | None = None,
    enqueue: bool = False,
) -> dict:
    """Envia notificacao para usuarios ou para todos.

    `recipients`: "*" envia para todos; lista de usuarios envia para cada um.
    `data`: dict opcional (payload customizado acessiveis no handler do app).
    """
    if not title:
        title = frappe.get_cached_doc("FCM Settings").get("default_title") or _("Notificacao")
    if not recipients:
        recipients = frappe.session.user

    if recipients == "*" or recipients == "all":
        return services.send_to_all(title, body, data=data, image=image, enqueue=enqueue)

    users = recipients if isinstance(recipients, list) else [recipients]
    return services.send_to_users(users, title, body, data=data, image=image, enqueue=enqueue)


@frappe.whitelist()
def test_connection() -> dict:
    """Valida o service account e a autenticacao OAuth2 com o Firebase (sem enviar)."""
    from erpnext_fcm.firebase.client import get_project_id, get_session

    project_id = get_project_id()
    session = get_session()
    # Forca a emissao do token de acesso para validar as credenciais.
    from google.auth.transport.requests import Request as AuthRequest

    session.credentials.refresh(AuthRequest())
    token = session.credentials.token
    return {
        "status": "ok",
        "project_id": project_id,
        "token_issued": bool(token),
    }

