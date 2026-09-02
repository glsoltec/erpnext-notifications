// ERPNext Notifications - registro de push no navegador (Web/PWA)
// Carrega o SDK do Firebase, registra o service worker em /sw.js, obtem o token
// FCM e o vincula ao usuario logado via erpnext_notifications.api.subscribe.

/* global firebase, frappe */

(function () {
  "use strict";

  const FIREBASE_SDK_VERSION = "10.8.0";
  const TOKEN_KEY = "erpnext_notifications_token";

  // SRI (integrity) das versoes homologadas do SDK no CDN do Google.
  const FIREBASE_SRI = {
    "firebase-app-compat.js":
      "sha384-4gq9w/AGf72FXdNQ3Kn3EqWP7633NbCMjpYHt8YCZyXf23o2opcuAr4cif41tLrC",
    "firebase-messaging-compat.js":
      "sha384-F8rlC59erkC9PkWp7FIVgQHXhGqSCrhQS1i1zIWYJORAsFGQZE+do+ct+jlO2+0z",
  };

  function loadScript(src, integrity) {
    return new Promise(function (resolve, reject) {
      if (document.querySelector('script[src="' + src + '"]')) {
        resolve();
        return;
      }
      const s = document.createElement("script");
      s.src = src;
      s.crossOrigin = "anonymous";
      if (integrity) {
        s.integrity = integrity;
      }
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  function loadFirebaseCompatSdk() {
    const base =
      "https://www.gstatic.com/firebasejs/" + FIREBASE_SDK_VERSION + "/";
    const appFile = "firebase-app-compat.js";
    const msgFile = "firebase-messaging-compat.js";
    return loadScript(base + appFile, FIREBASE_SRI[appFile]).then(function () {
      return loadScript(base + msgFile, FIREBASE_SRI[msgFile]);
    });
  }

  function injectManifest(settings) {
    if (!document.querySelector('link[rel="manifest"]')) {
      const link = document.createElement("link");
      link.rel = "manifest";
      link.href = "/manifest.json";
      document.head.appendChild(link);
    }
    const meta = document.createElement("meta");
    meta.name = "theme-color";
    meta.content = "#2490EF";
    document.head.appendChild(meta);
  }

  function showForegroundNotification(payload) {
    if (!("Notification" in window) || Notification.permission !== "granted") {
      return;
    }
    const d = payload.data || {};
    const title = d.title || "Notificação";
    const options = { body: d.body || "" };
    if (d.notification_icon) {
      options.icon = d.notification_icon;
    }
    const n = new Notification(title, options);
    if (d.click_action) {
      n.onclick = function () {
        window.open(d.click_action, "_blank");
      };
    }
  }

  function initFcm() {
    if (!("serviceWorker" in navigator) || !("Notification" in window)) {
      return;
    }

    frappe
      .xcall("erpnext_notifications.api.get_web_config")
      .then(function (cfg) {
        if (!cfg || !cfg.config || !cfg.vapid_public_key) {
          return;
        }
        injectManifest(cfg);

        return loadFirebaseCompatSdk().then(function () {
          const encoded = encodeURIComponent(JSON.stringify(cfg.config));
          return navigator.serviceWorker
            .register("/sw.js?config=" + encoded)
            .then(function (registration) {
              return Notification.requestPermission().then(
                function (permission) {
                  if (permission !== "granted") {
                    return;
                  }
                  firebase.initializeApp(cfg.config);
                  const messaging = firebase.messaging();
                  return messaging
                    .getToken({
                      vapidKey: cfg.vapid_public_key,
                      serviceWorkerRegistration: registration,
                    })
                    .then(function (token) {
                      if (!token) {
                        return;
                      }
                      messaging.onMessage(showForegroundNotification);
                      if (localStorage.getItem(TOKEN_KEY) === token) {
                        return;
                      }
                      return frappe
                        .xcall("erpnext_notifications.api.subscribe", {
                          fcm_token: token,
                        })
                        .then(function () {
                          localStorage.setItem(TOKEN_KEY, token);
                        });
                    });
                },
              );
            });
        });
      })
      .catch(function (err) {
        console.log("[FCM] Push web nao inicializado:", err.message || err);
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (
      typeof frappe === "undefined" ||
      !frappe.session ||
      frappe.session.user === "Guest"
    ) {
      return;
    }
    initFcm();
  });
})();
