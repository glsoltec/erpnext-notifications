from __future__ import annotations

import frappe
from frappe.model.document import Document


class FCMDevice(Document):
    def validate(self):
        self.sanitize_token()
        self.set_user_if_missing()

    def sanitize_token(self):
        if self.token:
            self.token = self.token.strip()

    def set_user_if_missing(self):
        # Permite registro via API sem informar usuario (usa o usuario logado).
        if not self.user and frappe.session.user:
            self.user = frappe.session.user

    def deactivate(self, reason=None):
        self.is_active = 0
        self.last_error = (reason or "")[:140]
        self.flags.ignore_permissions = True
        self.save(ignore_permissions=True)
