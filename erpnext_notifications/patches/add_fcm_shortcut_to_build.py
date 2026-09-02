import frappe

SHORTCUT = {
    "label": "FCM Settings",
    "type": "DocType",
    "link_to": "FCM Settings",
    "color": "blue",
    "icon": "octicon octicon-bell",
}


def execute():
    if not frappe.db.exists("FCM Settings"):
        return

    workspace_name = "Build"
    if not frappe.db.exists("Workspace", workspace_name):
        return

    workspace = frappe.get_doc("Workspace", workspace_name)
    for shortcut in workspace.shortcuts:
        if shortcut.get("link_to") == SHORTCUT["link_to"]:
            return

    workspace.append("shortcuts", SHORTCUT)
    workspace.flags.ignore_permissions = True
    workspace.save(ignore_permissions=True)