import json

import frappe

WORKSPACE_NAME = "Build"
SHORTCUT_LABEL = "FCM Settings"
SHORTCUT = {
    "label": SHORTCUT_LABEL,
    "type": "DocType",
    "link_to": SHORTCUT_LABEL,
    "doc_view": "List",
    "stats_filter": "[]",
    "color": "blue",
    "icon": "octicon octicon-bell",
}


def after_migrate():
    """Garante o atalho FCM Settings no workspace Build (idempotente).

    O workspace 'Build' é padrão do frappe e seu `content` pode ser re-sincronizado
    no migrate. Este hook roda depois de `sync_all` e re-adiciona o bloco shortcut
    e o child `Workspace Shortcut` sempre que necessário.
    """
    if not frappe.db.exists("FCM Settings"):
        return
    if not frappe.db.exists("Workspace", WORKSPACE_NAME):
        return

    workspace = frappe.get_doc("Workspace", WORKSPACE_NAME)

    shortcut_name = _ensure_shortcut(workspace)
    _ensure_content_block(workspace)

    workspace.flags.ignore_permissions = True
    workspace.save(ignore_permissions=True)
    frappe.db.commit()


def _ensure_shortcut(workspace) -> str | None:
    for shortcut in workspace.shortcuts:
        if shortcut.get("link_to") == SHORTCUT_LABEL:
            for field, value in SHORTCUT.items():
                shortcut.set(field, value)
            return shortcut.get("name")

    shortcut = workspace.append("shortcuts", SHORTCUT)
    return shortcut.get("name")


def _ensure_content_block(workspace):
    try:
        content = json.loads(workspace.content) if workspace.content else []
    except (json.JSONDecodeError, TypeError):
        content = []

    for block in content:
        if block.get("type") == "shortcut" and block.get("data", {}).get("shortcut_name") == SHORTCUT_LABEL:
            return

    content.append(
        {
            "id": f"fcm-settings-{frappe.utils.cstr(workspace.name)}",
            "type": "shortcut",
            "data": {"shortcut_name": SHORTCUT_LABEL, "col": 3},
        }
    )
    workspace.content = json.dumps(content, ensure_ascii=False)