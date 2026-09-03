import frappe

ICON_NAME = "FCM Settings"
PARENT_ICON = "Framework"


def execute():
    if not frappe.db.exists("FCM Settings"):
        return

    if frappe.db.exists("Desktop Icon", ICON_NAME):
        return

    frappe.get_doc(
        {
            "doctype": "Desktop Icon",
            "name": ICON_NAME,
            "label": ICON_NAME,
            "app": "erpnext_notifications",
            "icon_type": "DocType",
            "link_type": "DocType",
            "link_to": ICON_NAME,
            "parent_icon": PARENT_ICON,
            "sidebar": 0,
            "standard": 0,
            "restrict_removal": 0,
            "hidden": 0,
            "idx": 0,
        }
    ).insert(ignore_permissions=True)