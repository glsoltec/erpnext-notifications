# ERPNext Notifications

Push notifications for Frappe/ERPNext users through Firebase Cloud Messaging
(FCM v1), with browser/PWA registration, Notification Log relay and configurable
document-event rules.

## What It Does

- Sends web push notifications from the ERPNext Desk/PWA.
- Relays native Frappe `Notification Log` entries to the user's active devices.
- Supports multiple active devices per user.
- Sends to browser, Android or other compatible FCM clients that register a token.
- Provides automatic rules for document events such as submit, cancel, update and
  insert.
- Supports Jinja templates with the event document and recipient context.
- Uses asynchronous Frappe jobs for delivery.
- Records delivery status, provider message ID, errors and retry information.
- Retries transient provider errors using backoff and stops retrying invalid tokens.
- Deactivates invalid tokens according to `auto_remove_invalid`.
- Provides a PWA manifest and scoped service worker for static asset caching.

The app does not include a native Android or iOS application. Native clients must
obtain an FCM token and register it through the API described below.

## Compatibility

- Frappe Framework: `16.x`
- ERPNext: `16.x`
- Python: `3.10` or newer
- Browser push: HTTPS is required; browser support depends on the browser and
  operating system.
- Firebase Cloud Messaging HTTP v1 and Web Push VAPID are required for delivery.

The `version-16` branch is the supported branch for this release line.

## Installation

### From Frappe Marketplace

Use the Marketplace installation flow for the target Frappe Cloud site. After the
app is installed, run the site migration and build steps if the platform requests
them.

### From GitHub

Run the commands as the bench owner, normally `frappe`:

```bash
cd /home/frappe/frappe-bench
bench get-app https://github.com/glsoltec/erpnext-notifications --branch version-16
bench --site SITE_NAME install-app erpnext_notifications
bench --site SITE_NAME migrate
bench build --app erpnext_notifications
bench --site SITE_NAME clear-cache
bench restart
```

Replace `SITE_NAME` with the actual site name. The app requires Frappe and ERPNext
16.x. Do not run these commands against production without a current backup and a
maintenance window appropriate for the migration.

### Update

Before updating, back up the site and database. Then update the app, migrate and
rebuild assets:

```bash
cd /home/frappe/frappe-bench
bench update --app erpnext_notifications
bench --site SITE_NAME migrate
bench build --app erpnext_notifications
bench --site SITE_NAME clear-cache
bench restart
```

Review the release notes and branch compatibility before updating between major
Frappe versions.

### Uninstall

Uninstallation can remove app data. Back up first and review the data-retention
requirements:

```bash
bench --site SITE_NAME backup --with-files
bench --site SITE_NAME uninstall-app erpnext_notifications
```

## Firebase Setup

Create a Firebase project dedicated to the environment or organization, enable
Cloud Messaging, and use HTTPS for the ERPNext site.

### Service Account

1. Open Firebase Console and select the project.
2. Go to **Project settings → Service accounts**.
3. Generate a private key for the service account.
4. Open **FCM Settings** in ERPNext as a System Manager.
5. Paste the complete service-account JSON in **Service Account JSON**.
6. Save the document and confirm that **Project ID** is populated.
7. Click **Testar conexão**.

Never commit this JSON, send it through chat, or place it in a public repository.
The `.gitignore` excludes common Firebase service-account filenames, but secrets
must still be handled by the deployment team.

If the service-account JSON is exposed in any way (logs, console output, chat,
repository), **rotate the Firebase service account** by generating a new private
key in the Firebase Console and updating `FCM Settings`. Treat the private key as
a credential that grants message-sending rights for the project.

### Web/PWA Configuration

In Firebase:

1. Go to **Project settings → General → Your apps**.
2. Create or select a Web app.
3. Copy its `firebaseConfig` object.
4. Go to **Project settings → Cloud Messaging**.
5. Generate or copy the public Web Push VAPID key.

In ERPNext, open **FCM Settings** at:

```text
/app/fcm-settings
```

In **Web / PWA**, enable browser push and fill:

- **Firebase Web Config**: the Web app configuration JSON;
- **VAPID Public Key**: the public Web Push certificate key.

Example structure, using placeholders only:

```json
{
  "apiKey": "API_KEY_AQUI",
  "authDomain": "projeto.firebaseapp.com",
  "projectId": "projeto-firebase",
  "storageBucket": "projeto.firebasestorage.app",
  "messagingSenderId": "SENDER_ID_AQUI",
  "appId": "APP_ID_AQUI"
}
```

The Web Config values are client-side Firebase configuration values and are not a
replacement for the private service-account JSON. Confirm that the Web Config
`projectId` and service-account project are the same.

After loading the Desk, click **Ativar notificações** when the button appears.
The browser permission request is intentionally triggered by this user action;
modern browsers may ignore automatic permission requests made during page load.

### Browser Requirements

- The ERPNext site must use HTTPS.
- The user must be authenticated in the Desk.
- The browser must allow notifications for the ERPNext origin.
- The browser must support service workers and Firebase Web Push.
- A Content Security Policy, if configured, must allow the Firebase CDN and the
  required Firebase endpoints.

## FCM Settings

`FCM Settings` is a Single DocType and is restricted to System Manager.

### General Settings

- **Habilitar notificações**: enables server-side FCM delivery.
- **Service Account JSON**: private Firebase service-account JSON.
- **Project ID**: populated from the service account when possible.
- **Título padrão**: title used when a notification has no title.
- **Tamanho do lote**: maximum number of logs processed by scheduled jobs.
- **Gravar log de notificações**: enables delivery logs.
- **Desativar tokens inválidos automaticamente**: deactivates invalid FCM tokens.
- **Retenção de logs**: number of days before old logs are removed.

### Web/PWA Settings

- **Habilitar push no navegador** (`enable_fcm`): must be enabled for the browser
  registration flow. The web JavaScript calls `get_web_config`, which throws when
  this option is off, so the enable button and device registration do not run.
- **Firebase Web Config**: the Web app configuration as **valid JSON**. Keys must
  use double quotes. A JavaScript object literal such as
  `{ apiKey: "..." }` is not accepted and breaks `json.loads`.
- **VAPID Public Key**: the public Web Push certificate key.

Example of a valid **Firebase Web Config** (placeholders only):

```json
{
  "apiKey": "API_KEY_AQUI",
  "authDomain": "projeto.firebaseapp.com",
  "projectId": "projeto-firebase",
  "storageBucket": "projeto.firebasestorage.app",
  "messagingSenderId": "SENDER_ID_AQUI",
  "appId": "APP_ID_AQUI"
}
```

If the saved Web Config is invalid JSON, `get_web_config` returns an error and the
browser cannot register. Use **Testar conexão** and the browser console to confirm
there are no Firebase JSON errors.

> Note: a notification is delivered only when the recipient has at least one
> **active registered device** in `FCM Device`. A successful `send` call with
> `tokens: 0` means the target user has no device registered; the user must enable
> browser push (or a native client must register its token) before the message can
> be delivered.

### PWA Settings

Configure the app name, short name, description, colors, start URL, scope,
display, orientation and icons. The endpoints are:

```text
/manifest.json
/sw.js
```

The service worker caches only same-origin static assets under its own cache
namespace. It does not cache ERPNext API responses or dynamic Desk pages.

## Automatic Rules

Rules are configured in the **Regras de Notificação** table inside `FCM Settings`.

Each rule contains:

- **Habilitado**
- **DocType**
- **Evento**: `after_insert`, `on_update`, `on_submit` or `on_cancel`
- **Campo do destinatário**
- **Título** (Jinja)
- **Mensagem** (Jinja)
- **Dados extras** (JSON/Jinja)

Example:

```text
DocType: Sales Order
Evento: on_submit
Campo do destinatário: owner
Título: Pedido {{ doc.name }} aprovado
Mensagem: O pedido {{ doc.name }} foi enviado para processamento.
```

If the recipient field is empty, the rule falls back to `owner`. The recipient
must contain a valid ERPNext user identifier.

The app currently registers event hooks for `Sales Invoice`, `Purchase Invoice`,
`Leave Application`, `Issue`, `ToDo` and `Notification Log`. Add or adjust hooks
in a controlled release if other DocTypes are required.

## Native Notification Log Relay

The app listens to Frappe `Notification Log` entries and sends a push to the
`for_user` recipient. This covers common Frappe notifications such as mentions,
assignments, shares, alerts and energy-point updates.

The notification body is stripped of HTML and truncated before delivery. The
document link is included as a safe HTTPS or relative URL when available.

## Device Lifecycle

When browser push is enabled, the Desk JavaScript:

1. Retrieves the public Web Config.
2. Loads the pinned Firebase compatibility SDK.
3. Registers `/sw.js`.
4. Requests browser notification permission.
5. Obtains the browser FCM token.
6. Registers the token for the logged-in user.

Device records are stored in `FCM Device`. Users can register and deactivate only
their own devices through the API. Full device records and notification logs are
restricted to System Manager.

## API

All endpoints are authenticated through the normal Frappe session or a valid API
credential. Mutating endpoints accept POST only.

### Register a Device

```text
POST /api/method/erpnext_notifications.api.register_device
```

Arguments:

```json
{
  "token": "FCM_TOKEN_AQUI",
  "device_type": "Web",
  "app_version": "1.0.0",
  "user_agent": "PWA"
}
```

A token already owned by another user cannot be reattached.

### List Own Devices

```text
GET /api/method/erpnext_notifications.api.get_my_devices
```

The response contains `token_masked`, not the full FCM token.

### Unregister a Device

```text
POST /api/method/erpnext_notifications.api.unregister_device
```

The token must belong to the current session user.

### Send a Notification

```text
POST /api/method/erpnext_notifications.api.send_notification
```

This endpoint requires the **System Manager** role. Use `recipients="*"` only
when a global broadcast is intended.

Server-side example:

```python
frappe.call(
    "erpnext_notifications.api.send_notification",
    recipients=["user@empresa.com.br"],
    title="Pedido aprovado",
    body="Seu pedido foi aprovado.",
    data={"document": "SO-0001"},
    enqueue=True,
)
```

### Web Configuration

```text
GET /api/method/erpnext_notifications.api.get_web_config
```

This returns only the public Firebase Web Config and VAPID public key. It does
not return the private service-account JSON.

### Test Firebase Connection

```text
POST /api/method/erpnext_notifications.api.test_connection
```

The endpoint requires System Manager and validates the service-account OAuth
credentials. It does not send a notification.

## Logs and Operations

Use **FCM Notification Log** to inspect:

- title and body;
- recipient and device;
- delivery status;
- FCM message ID;
- provider error;
- attempt count;
- next retry time;
- last attempt time.

Statuses include:

```text
Queued
Sent
Failed
Invalid Token
```

Transient failures use scheduled retry with backoff. Invalid tokens are marked
non-retryable and can be deactivated according to configuration.

## Permissions and Security

- `FCM Settings`: System Manager only.
- `FCM Device`: System Manager in the Desk; user self-service through scoped API.
- `FCM Notification Log`: System Manager only.
- Manual `send_notification`: System Manager only.
- Device registration: authenticated user and own token scope.
- Mutating API methods: POST only.
- Service-account JSON: never commit or expose publicly.
- Push links: HTTPS or relative paths only.
- FCM tokens: masked in user-facing device list responses.

Read [`SECURITY.md`](SECURITY.md) before deploying the app.

## Troubleshooting

### “Falha ao obter o método” or import error

Confirm the app is on the correct branch and restart workers after updating:

```bash
bench --site SITE_NAME migrate
bench --site SITE_NAME clear-cache
bench build --app erpnext_notifications
bench restart
```

### Test connection fails

Check:

- the service-account JSON is complete and valid;
- its project matches the Firebase Web Config project;
- Cloud Messaging is enabled;
- the site user is System Manager;
- the server can reach Google OAuth and FCM over HTTPS.

### Browser does not request permission

Check:

- the site is HTTPS;
- the user is not Guest;
- browser notification permission is not blocked;
- service workers are allowed;
- the browser console has no CSP or Firebase errors;
- `/manifest.json` and `/sw.js` return HTTP 200.

If the browser permission was previously denied, open the site permissions for
the ERPNext origin, reset **Notifications** to **Ask** or **Allow**, reload the
Desk and click **Ativar notificações**. The prompt is not shown again while the
permission remains denied.

### Notification is queued but not delivered

Check `FCM Notification Log`, active `FCM Device` records and worker status:

```bash
bench doctor
bench --site SITE_NAME show-pending-jobs
```

Confirm that the Frappe short worker and scheduler are running.

### Token becomes invalid

This is expected after browser data removal, app reinstall, token rotation or
Firebase project changes. The scheduler marks the token invalid and deactivates
it when `auto_remove_invalid` is enabled. The user must register the device again.

## Development

The app uses a standard Frappe package layout:

```text
erpnext_notifications/
├── api.py
├── hooks.py
├── methods.py
├── services.py
├── scheduler.py
├── validation.py
├── firebase/
├── fcm_notifications/doctype/
├── public/js/
└── www/
```

Run the dependency-free unit tests:

```bash
python -m unittest discover -s tests
```

Frappe integration tests must run inside a bench with a disposable Frappe/ERPNext
16 site. Do not test broadcast notifications against production.

## Marketplace Readiness

The repository includes:

- MIT license;
- `MANIFEST.in`;
- `modules.txt` and `patches.txt`;
- `SECURITY.md`;
- compatibility metadata in `pyproject.toml`;
- installation and operational documentation;
- unit tests independent of bench;
- GitHub Actions workflow for lint, SAST, dependency and secret checks.

See [`docs/marketplace-readiness.md`](docs/marketplace-readiness.md) for the
release checklist. Marketplace publication still requires a publisher account,
profile assets, a clean-site integration test, passing GitHub checks and review
by Frappe.

## License

MIT. See [`LICENSE`](LICENSE).
