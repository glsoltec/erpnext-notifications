// ERPNext Notifications - registro de push no navegador (Web/PWA)
// Carrega o SDK do Firebase, registra o service worker em /sw.js, obtem o token
// FCM e o vincula ao usuario logado via erpnext_notifications.api.subscribe.

/* global firebase, frappe */

(function () {
  "use strict";

  const FIREBASE_SDK_VERSION = "10.8.0";
  const ENABLE_BUTTON_ID = "erpnext-notifications-enable";

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
    meta.content = (settings && settings.theme_color) || "#2490EF";
    document.head.appendChild(meta);
  }

  function tokenStorageKey() {
    const user = (frappe.session && frappe.session.user) || "anonymous";
    return "erpnext_notifications_token:" + encodeURIComponent(user);
  }

  function removeEnableButton() {
    const button = document.getElementById(ENABLE_BUTTON_ID);
    if (button) {
      button.remove();
    }
  }

  function requestNotificationPermission() {
    if (Notification.permission !== "default") {
      return Promise.resolve(Notification.permission);
    }
    return Notification.requestPermission();
  }

  function showEnableButton(onClick) {
    if (document.getElementById(ENABLE_BUTTON_ID)) {
      return;
    }

    const button = document.createElement("button");
    button.id = ENABLE_BUTTON_ID;
    button.type = "button";
    button.textContent = "Ativar notificações";
    button.setAttribute("aria-label", "Ativar notificações push");
    button.style.cssText =
      "position:fixed;right:24px;bottom:24px;z-index:1080;padding:10px 16px;" +
      "border:0;border-radius:6px;background:#2490ef;color:#fff;font-weight:600;" +
      "box-shadow:0 2px 8px rgba(0,0,0,.2);cursor:pointer";
    button.addEventListener("click", function () {
      button.disabled = true;
      onClick()
        .then(function () {
          removeEnableButton();
        })
        .catch(function (err) {
          button.disabled = false;
          console.log("[FCM] Permissão não concedida:", err.message || err);
        });
    });
    document.body.appendChild(button);
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
              firebase.initializeApp(cfg.config);
              const messaging = firebase.messaging();

              function registerToken() {
                return requestNotificationPermission().then(
                  function (permission) {
                    if (permission !== "granted") {
                      return;
                    }
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
                        const storageKey = tokenStorageKey();
                        if (localStorage.getItem(storageKey) === token) {
                          return;
                        }
                        return frappe
                          .xcall("erpnext_notifications.api.subscribe", {
                            fcm_token: token,
                          })
                          .then(function () {
                            localStorage.setItem(storageKey, token);
                          });
                      });
                  },
                );
              }

              if (Notification.permission === "granted") {
                return registerToken();
              }
              if (Notification.permission === "default") {
                showEnableButton(registerToken);
              }
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
