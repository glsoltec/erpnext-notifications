// ERPNext Notifications - Service Worker (web push / FCM background + offline shell)
// O config do Firebase chega pela query string no momento do registro:
// navigator.serviceWorker.register('/sw.js?config=<encoded-json>')
//
// Nota: importScripts() nao aceita atributo SRI/integrity. O SDK e carregado do
// CDN oficial do Google com versao fixada (10.8.0) e auditada. O loader da
// pagina (public/js/erpnext_notifications_web.js) usa SRI para os mesmos
// arquivos. Ao atualizar a versao, atualize tambem o SRI do loader da pagina.

var fcmConfigParam = new URL(location).searchParams.get("config");
var CACHE_PREFIX = "erpnext-notifications-";
var STATIC_CACHE = "erpnext-notifications-static-v1";
var messaging = null;

self.addEventListener("install", function (event) {
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    Promise.all([
      self.clients.claim(),
      caches.keys().then(function (keys) {
        return Promise.all(
          keys
            .filter(function (k) {
              // Remove apenas caches desta app, preservando os de outras apps.
              return k.indexOf(CACHE_PREFIX) === 0 && k !== STATIC_CACHE;
            })
            .map(function (k) {
              return caches.delete(k);
            }),
        );
      }),
    ]),
  );
});

// Cache offline seguro: apenas assets estaticos same-origin (CSS/JS/imgs/fonts).
// Nao cachear paginas dinamicas do Desk nem respostas de API.
self.addEventListener("fetch", function (event) {
  var req = event.request;
  if (req.method !== "GET") return;

  var url = new URL(req.url);
  var isSameOrigin = url.origin === self.location.origin;

  if (
    isSameOrigin &&
    /\.(css|js|woff2?|ttf|png|jpe?g|gif|svg|webp|ico)$/i.test(url.pathname)
  ) {
    event.respondWith(
      caches.match(req).then(function (cached) {
        if (cached) return cached;
        return fetch(req).then(function (resp) {
          if (resp && resp.status === 200) {
            const clone = resp.clone();
            caches.open(STATIC_CACHE).then(function (cache) {
              cache.put(req, clone);
            });
          }
          return resp;
        });
      }),
    );
  }
  // Navegacoes nao sao interceptadas: sem promessa de offline falso.
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
    messaging = firebase.messaging();

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
