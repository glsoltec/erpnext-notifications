from __future__ import annotations

import json

import frappe
from frappe.model.document import Document


class FCMSettings(Document):
    def validate(self):
        self.set_project_id()

    def set_project_id(self):
        if not self.service_account_json:
            return
        project = None
        try:
            sa = json.loads(self.service_account_json)
            project = sa.get("project_id")
        except (json.JSONDecodeError, TypeError):
            frappe.throw(
                frappe._("service_account_json em FCM Settings não é um JSON válido.")
            )
        if project and self.get("project_id") != project:
            self.project_id = project

    @frappe.whitelist()
    def get_service_account(self):
        """Retorna o dict da conta de serviço (somente System Manager)."""
        frappe.only_for("System Manager")
        if not self.service_account_json:
            frappe.throw(frappe._("Service account não configurado em FCM Settings."))
        try:
            return json.loads(self.service_account_json)
        except json.JSONDecodeError:
            frappe.throw(frappe._("service_account_json inválido em FCM Settings."))
