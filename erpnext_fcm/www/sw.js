// ERPNext FCM - Service Worker (web push / FCM background)
// O config do Firebase chega pela query string no momento do registro:
// navigator.serviceWorker.register('/sw.js?config=<encoded-json>')

var fcmConfigParam = new URL(location).searchParams.get("config");

self.addEventListener("install", function (event) {
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(self.clients.claim());
});

// FCM em segundo plano (aba fechada)
try {
  if (fcmConfigParam) {
    importScripts(
      "https://www.gstatic.com/firebasejs/10.8.0/firebase-app-compat.js",
    );
    importScripts(
      "https://www.gstatic.com/firebasejs/10.8.0/firebase-messaging-compat.js",
    );

    firebase.initializeApp(JSON.parse(fcmConfigParam));
    var messaging = firebase.messaging();

    messaging.onBackgroundMessage(function (payload) {
      var d = payload.data || {};
      var title = d.title || "Notificação";
      var opts = { body: d.body || "", tag: "erpnext-fcm" };
      if (d.notification_icon) {
        opts.icon = d.notification_icon;
      }
      if (d.click_action) {
        opts.data = { url: d.click_action };
      }
      self.registration.showNotification(title, opts);
    });
  }
} catch (err) {
  console.error("[SW] FCM init failed", err);
}

self.addEventListener("notificationclick", function (event) {
  event.notification.close();
  var url = event.notification.data && event.notification.data.url;
  if (url) {
    event.waitUntil(clients.openWindow(url));
  }
});
