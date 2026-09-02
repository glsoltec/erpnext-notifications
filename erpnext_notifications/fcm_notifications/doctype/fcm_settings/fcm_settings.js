frappe.ui.form.on("FCM Settings", {
  refresh: function (frm) {
    if (frm.doc.__onload && frm.doc.__onload.disable_send) return;

    frm.add_custom_button(
      __("Testar conexão"),
      function () {
        frappe.call({
          method: "erpnext_notifications.api.test_connection",
          callback: function (r) {
            if (r.message && r.message.status === "ok") {
              frappe.msgprint(
                __("Conexão OK. Project ID: {0}", [r.message.project_id]),
              );
            } else {
              frappe.msgprint(__(r.message || "Falha ao testar conexão."));
            }
          },
          error: function (r) {
            frappe.msgprint(__(r.message || "Falha ao testar conexão."));
          },
        });
      },
      __("Firebase"),
    );
  },
});
