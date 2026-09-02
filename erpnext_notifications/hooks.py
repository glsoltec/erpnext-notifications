from __future__ import annotations

app_name = "erpnext_notifications"
app_title = "ERPNext Notifications"
app_publisher = "GL SOLTEC"
app_description = "Notificacoes push (PWA e web) para usuarios do ERPNext via Firebase Cloud Messaging (FCM v1)."
app_icon = "octicon octicon-bell"
app_color = "blue"
app_email = "contato@glsoltec.com.br"
app_license = "MIT"
app_version = "0.1.0"
app_url = "https://github.com/glsoltec/erpnext-notifications"

required_apps = ["frappe", "erpnext"]

# ---------------------------------------------------------------------------
# Permissoes de acesso a pacotes
# ---------------------------------------------------------------------------
app_include_js = [
    "erpnext_notifications_web.js",
]

# ---------------------------------------------------------------------------
# DocTypes e modulos
# ---------------------------------------------------------------------------
modules = [
    "App Notifications",
]

# ---------------------------------------------------------------------------
# Envio por eventos de documento (regras configuraveis em FCM Settings)
# A funcao eh a mesma para todos; o filtro real (doctype + evento) e feito
# pelas "FCM Notification Rules" em FCM Settings. Adicione/remova doctypes
# conforme necessidade sem mudar codigo.
# ---------------------------------------------------------------------------
doc_events = {
    "Sales Invoice": {
        "on_submit": "erpnext_notifications.methods.handle_doc_event",
        "on_cancel": "erpnext_notifications.methods.handle_doc_event",
    },
    "Purchase Invoice": {
        "on_submit": "erpnext_notifications.methods.handle_doc_event",
        "on_cancel": "erpnext_notifications.methods.handle_doc_event",
    },
    "Leave Application": {
        "on_update": "erpnext_notifications.methods.handle_doc_event",
    },
    "Issue": {
        "after_insert": "erpnext_notifications.methods.handle_doc_event",
    },
    "ToDo": {
        "after_insert": "erpnext_notifications.methods.handle_doc_event",
    },
    "Notification Log": {
        "after_insert": "erpnext_notifications.methods.send_notification_log_push",
    },
}

# ---------------------------------------------------------------------------
# Tarefas agendadas
# ---------------------------------------------------------------------------
scheduler_events = {
    "all": [
        "erpnext_notifications.scheduler.retry_failed_notifications",
    ],
    "daily": [
        "erpnext_notifications.scheduler.cleanup_old_logs",
        "erpnext_notifications.scheduler.cleanup_invalid_devices",
    ],
}

# ---------------------------------------------------------------------------
# Alteracoes de schema (Fixtures/Print) e translacao
# ---------------------------------------------------------------------------
fixtures = []
