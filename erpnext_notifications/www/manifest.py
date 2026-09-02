import json

import frappe

no_sitemap = 1


def get_context(context):
    s = frappe.get_cached_doc("FCM Settings")

    context.app_name = s.manifest_name or "ERPNext"
    context.app_short_name = s.manifest_short_name or "ERPNext"
    context.app_description = s.manifest_description or ""
    context.theme_color = s.manifest_theme_color or "#2490EF"
    context.background_color = s.manifest_background_color or "#FFFFFF"
    context.start_url = s.manifest_start_url or "/app"
    context.app_scope = s.manifest_scope or "/"
    context.display = s.manifest_display or "standalone"
    context.orientation = s.manifest_orientation or "portrait"
    context.lang = "pt-BR"

    icons = [
        {"src": i.src, "sizes": i.sizes or "512x512", "type": i.type or "image/png"}
        for i in s.pwa_icons
    ]
    if not icons:
        icons = [
            {"src": "/assets/frappe/images/favicon.png", "sizes": "128x128", "type": "image/png"}
        ]
    context.icons = json.dumps(icons)