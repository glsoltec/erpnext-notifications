from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _

from erpnext_notifications import services
from erpnext_notifications.validation import (
    _detect_device_type,
    _validate_token_format,
    mask_token,
    normalize_recipients,
    validate_payload,
)


def _require_post():
    """Endpoints com efeito colateral devem ser chamados apenas via POST.

    Reduz o risco de CSRF/GET com efeito colateral (o framework nao exige
    token CSRF em GET, e whitelisted methods podem ser invocados por GET).
    """
    if not frappe.request or frappe.request.method != "POST":
        frappe.throw(_("Metodo HTTP nao permitido. Use POST."), exc_class=frappe.PermissionError)


def _rate_limit(key: str, limit: int, window_seconds: int = 60):
    """Limita chamadas por janela de tempo usando o Redis (frappe.cache)."""
    import time

    redis_key = f"fcm:rl:{key}"
    now = int(time.time())
    bucket = int(now // window_seconds)
    counter_key = f"{redis_key}:{bucket}"

    count = frappe.cache.get(counter_key) or 0
    if count >= limit:
        frappe.throw(_("Limite de tentativas excedido. Tente novamente em instantes."), exc_class=frappe.PermissionError)

    frappe.cache.set(counter_key, count + 1, expires_in_sec=window_seconds + 5)


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

    Chamado via: POST /api/method/erpnext_notifications.api.register_device
    """
    _require_post()
    try:
        token = _validate_token_format(token)
    except ValueError as exc:
        frappe.throw(_(str(exc)))
    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.throw(_("Autenticacao necessaria para registrar dispositivo."))

    current = frappe.db.get_value("FCM Device", {"token": token}, "name")
    if current:
        doc = frappe.get_doc("FCM Device", current)
        # F-03: um token so pode ser registrado pelo usuario que ja o possui.
        if doc.user != frappe.session.user:
            frappe.throw(
                _("Token ja registrado por outro usuario."),
                exc_class=frappe.PermissionError,
            )
        doc.flags.ignore_permissions = True
    else:
        doc = frappe.new_doc("FCM Device")
    doc.update(
        {
            "user": frappe.session.user,
            "token": token,
            "device_type": _detect_device_type(user_agent=user_agent, device_type=device_type),
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
    _require_post()
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
    """Lista os dispositivos ativos do usuario logado (token mascarado)."""
    devices = frappe.get_all(
        "FCM Device",
        filters={"user": frappe.session.user, "is_active": 1},
        fields=["name", "token", "device_type", "app_version", "last_seen"],
        ignore_permissions=True,
    )
    for dev in devices:
        dev["token_masked"] = mask_token(dev.get("token"))
        dev.pop("token", None)
    return devices


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
    _require_post()
    frappe.only_for("System Manager")

    try:
        cleaned = validate_payload(title, body, image, data)
    except ValueError as exc:
        frappe.throw(_(str(exc)))
        cleaned = {"title": "", "body": "", "image": None, "data": None}

    title, body, image, data = cleaned["title"], cleaned["body"], cleaned["image"], cleaned["data"]

    if not title:
        title = frappe.get_cached_doc("FCM Settings").get("default_title") or _("Notificacao")
    if not recipients:
        recipients = frappe.session.user

    try:
        users = normalize_recipients(recipients)
    except ValueError as exc:
        frappe.throw(_(str(exc)))
        users = []

    if users == ["*"]:
        return services.send_to_all(title, body, data=data, image=image, enqueue=enqueue)

    return services.send_to_users(users, title, body, data=data, image=image, enqueue=enqueue)


# ---------------------------------------------------------------------------
# Web / PWA (navegador)
# ---------------------------------------------------------------------------
@frappe.whitelist()
def get_web_config() -> dict:
    """Retorna o firebaseConfig + VAPID public key para o SDK web do navegador."""
    settings = frappe.get_cached_doc("FCM Settings")
    if not settings.enable_fcm:
        frappe.throw(_("Push no navegador (Web/PWA) nao habilitado em FCM Settings."))
    if not settings.fcm_web_config or not settings.fcm_vapid_public_key:
        frappe.throw(
            _("Configure 'Firebase Web Config' e 'VAPID Public Key' em FCM Settings (secao Web/PWA).")
        )
    try:
        config = json.loads(settings.fcm_web_config)
    except (json.JSONDecodeError, TypeError):
        frappe.throw(_("Firebase Web Config em FCM Settings nao e um JSON valido."))
        config = {}
    return {"config": config, "vapid_public_key": settings.fcm_vapid_public_key}


@frappe.whitelist()
def subscribe(fcm_token: str) -> dict:
    """Registra o navegador do usuario logado para receber push (device_type='Web')."""
    _require_post()
    return register_device(token=fcm_token, device_type="Web", user_agent="PWA")


@frappe.whitelist()
def unsubscribe(fcm_token: str) -> dict:
    """Desativa o token web do usuario logado."""
    _require_post()
    return unregister_device(token=fcm_token)


@frappe.whitelist()
def test_connection() -> dict:
    """Valida o service account e a autenticacao OAuth2 com o Firebase (sem enviar)."""
    _require_post()
    frappe.only_for("System Manager")
    from erpnext_notifications.firebase.client import get_project_id, get_session

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


@frappe.whitelist()
def send_test_notification() -> dict:
    """Envia uma notificacao de teste para o usuario logado (valida todo o fluxo)."""
    _require_post()
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Autenticacao necessaria para testar envio."), exc_class=frappe.PermissionError)

    _rate_limit(f"send_test:{user}", limit=3, window_seconds=60)

    out = services.send_to_user(
        user,
        title=_("Teste de Notificacao"),
        body=_("Esta e uma notificacao de teste enviada de FCM Settings."),
        data={"type": "test", "source": "fcm_settings"},
        enqueue=False,
    )
    return {"status": "sent", "user": user, "sent": out.get("sent", 0), "tokens": out.get("tokens", 0)}
