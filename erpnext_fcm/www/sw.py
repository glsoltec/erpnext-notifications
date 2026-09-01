import frappe

no_sitemap = 1


def get_context(context):
    context.web_include_js = frappe.get_hooks("web_include_js") or []
    context.web_include_css = frappe.get_hooks("web_include_css") or []
    context.favicon = "/assets/frappe/images/favicon.png"

    settings = frappe.get_single("Website Settings")
    if settings.favicon and settings.favicon != "attach_files:":
        context.favicon = settings.favicon