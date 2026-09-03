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

    frm.add_custom_button(
      __("Enviar notificação de teste"),
      function () {
        frappe.call({
          method: "erpnext_notifications.api.send_test_notification",
          callback: function (r) {
            if (r.message && r.message.status === "sent") {
              frappe.msgprint(
                __(
                  "Notificação de teste enviada para {0} ({1} dispositivo(s)).",
                  [r.message.user, r.message.sent],
                ),
              );
            } else {
              frappe.msgprint(
                __(r.message || "Nenhum dispositivo recebeu a notificação."),
              );
            }
          },
          error: function (r) {
            frappe.msgprint(
              __(r.message || "Falha ao enviar notificação de teste."),
            );
          },
        });
      },
      __("Firebase"),
    );
  },
});
