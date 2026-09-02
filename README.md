# ERPNext Notifications

Aplicativo customizado para o **ERPNext** que envia **notificações push** para
usuários em **PWA e web** via **Firebase Cloud Messaging (FCM v1)**.

- ⚡ **Web / PWA** — service worker, manifest e push no navegador (desk).
- 🔔 **Relay do Notification Log** — mentions, assignments, shares, energy points
  e alerts nativos do ERPNext viram push em todos os dispositivos do usuário.
- 🧩 **Regras por evento** — configure DocType + evento + destinatário + templates
  Jinja sem escrever código (ex.: aprovação de pedido, folha, tarefa).
- 📱 **Multi-dispositivo** — o mesmo usuário pode ter vários tokens ativos
  (mobile e web), todos recebem a notificação.
- 🛡️ **Robusto** — fila assíncrona, log de entrega, retry automático e
  desativação de tokens inválidos.

> Referência de PWA consultada: [omfsakib/pwa_frappe](https://github.com/omfsakib/pwa_frappe).

## Estrutura

```
erpnext_notifications/
├── api.py                 # Endpoints whitelisted (registro, envio, config web)
├── hooks.py               # doc_events, scheduler, app_include_js
├── methods.py             # Relay de Notification Log + regras por evento
├── services.py            # Orquestração de envio (fila, log, multi-token)
├── scheduler.py           # Retry, cleanup de logs e dispositivos inválidos
├── firebase/client.py     # Cliente HTTP FCM v1 (OAuth2 service account)
├── fcm_notifications/     # DocTypes: Settings, Device, Log, Rule, PWA Icon
├── public/js/             # Registro de push no navegador (desk)
└── www/                   # manifest.json, sw.js (service worker)
```

## Instalação

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/glsoltec/erpnext-notifications
bench install-app erpnext_notifications
bench migrate
bench build --app erpnext_notifications
```

Reinicie os processos (`bench restart`) e force o recarregamento do desk.

## Configuração

1. Crie um [projeto Firebase](https://console.firebase.google.com/) e habilite
   **Cloud Messaging**.
2. Em **Project Settings → Cloud Messaging → Web configuration**, gere o
   **certificado Web Push (par VAPID)** e copie a chave pública.
3. Em **Project Settings → General → Seus apps**, copie o **firebaseConfig** do
   app da Web (`apiKey`, `authDomain`, `projectId`, `storageBucket`,
   `messagingSenderId`, `appId`).
4. Gere uma **chave privada** da conta de serviço (Cloud Messaging) e copie o
   conteúdo JSON.
5. No ERPNext, abra **FCM Settings** (módulo FCM Notifications) e preencha:
   - **Service Account JSON** (da etapa 4) — preenche o Project ID automaticamente.
   - Marque **Habilitar notificações**.
   - Seção **Web / PWA**: marque **Habilitar push no navegador** e informe o
     **Firebase Web Config** (JSON) e a **VAPID Public Key**.
   - Use **Testar conexão** para validar o service account.
6. **Regras automáticas** (opcional): em FCM Settings → _Regras de Notificação_,
   defina DocType + evento + campo destinatário + templates Jinja.

> O push nativo do ERPNext (`Notification Log`) já funciona sem regras — assim que
> um admin configura o FCM, os usuários passam a receber push automaticamente.

## Uso programático

> **Autorização:** `send_notification` exige o papel **System Manager** e método **POST**.
> O auto-atendimento de dispositivos (`register_device`/`unregister_device`/`get_my_devices`)
> é restrito à própria sessão do usuário.

```python
# Enviar para um usuário (System Manager + POST)
frappe.call("erpnext_notifications.api.send_notification", {
    "recipients": "user@empresa.com.br",
    "title": "Pedido aprovado",
    "body": "Seu pedido foi aprovado.",
})
```

## Segurança

- Endpoints mutáveis aceitam somente **POST** (mitiga CSRF/GET com efeito colateral).
- `register_device` não permite reatribuir um token de outro usuário.
- Os DocTypes `FCM Device` e `FCM Notification Log` são acessíveis apenas a
  **System Manager**; usuários gerenciam os próprios dispositivos via API.
- O service account do Firebase é exposto apenas a **System Manager**
  (`get_service_account` valida o papel no servidor).
- O SDK do Firebase é carregado com **SRI** no loader da página; o service worker
  usa versão fixada (10.8.0) — veja nota em `www/sw.js`.
- O `.gitignore` protege service accounts (`*firebase-adminsdk*.json`). Não
  commitar arquivos de credencial.

### Validação de payload e limites

- `send_notification` valida título/corpo/imagem/`data` no servidor e rejeita
  payloads excessivos ou com objetos aninhados.
- URLs de notificação (`image`, `click_action`) aceitam somente `https://` ou
  caminhos relativos do próprio domínio.
- `get_my_devices` retorna o token **mascarado** (`token_masked`).
- Destinatários são normalizados e limitados por chamada.

### Retry e lifecycle

- Logs de token inválido recebem status **`Invalid Token`** e `retryable=0`,
  não sendo reprocessados.
- Falhas transitórias são reprocessadas com **backoff exponencial**
  (`next_retry_at`) até o limite configurado.
- A desativação automática de tokens respeita **`auto_remove_invalid`** em
  FCM Settings.
- Logs são gravados **por token** (usuário real do dispositivo), evitando valor
  inválido no campo `user` em envios multi-usuário.

## Contribuindo

Este app usa `pre-commit` (ruff, eslint, prettier, pyupgrade):

```bash
pre-commit install
```

## Testes

Testes unitários (sem dependência de bench/Frappe), usando `unittest`:

```bash
python -m unittest discover -s tests
```

## Licença

MIT
