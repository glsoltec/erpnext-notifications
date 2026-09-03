from __future__ import annotations

from frappe.model.document import Document

from erpnext_notifications.validation import mask_token


class FCMNotificationLog(Document):
    def validate(self):
        self.token_masked = mask_token(self.token) if self.token else ""
