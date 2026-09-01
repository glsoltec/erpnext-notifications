# ERPNext FCM

App customizado para o ERPNext/Frappe que envia **notificações push** via
**Firebase Cloud Messaging (FCM v1)** — a API atual do Google, autenticada por
conta de serviço (OAuth2). Simples, prático e de fácil manutenção.

## Recursos

- **Registro de dispositivos** por usuário (DocType `FCM Device`) + endpoints HTTP para o app.
- **Envio** para um usuário, vários usuários ou **todos** os dispositivos ativos.
- **Envio automático por evento** de documento via regras configuráveis (Jinja) em `FCM Settings`.
- **Log de notificações** (`FCM Notification Log`) com status, ID da mensagem e erros.
- **Tratamento de token inválido**: desativa automaticamente dispositivos com token vencido.
- **Tarefas agendadas**: reenvio de falhas temporárias e limpeza de logs/dispositivos antigos.
- **Botão "Testar conexão"** no FCM Settings para validar o service account.

## Requisitos

- Frappe / ERPNext **v15 ou v16**
- Python `>=3.10`
- Um projeto no [Firebase](https://console.firebase.google.com) com Cloud Messaging habilitado
- Dependência Python: `google-auth` (+ `requests`, já presente no Frappe)

## Instalação

```bash
# 1. Copie o app para o bench
cd /caminho/do/bench
cp -r /root/workspace/dev-apps/erpnext-fcm/erpnext_fcm apps/erpnext_fcm

# 2. Instale a dependencia no virtualenv do bench
bench pip install google-auth

# 3. Baixe e instale o app no site
bench get-app erpnext_fcm --skip-assets   # se ainda nao baixado via apps.txt
bench --site NOME_DO_SITE install-app erpnext_fcm
bench --site NOME_DO_SITE migrate
bench build
bench restart
```

> Se preferir, use `bench get-app https://github.com/glsoltec/erpnext-fcm.git`.

## Configuração

1. **Firebase**: console > Cloud Messaging. Garanta que a conta de serviço tenha permissão
   (o papel `Firebase Cloud Messaging API` deve estar presente; use **IAM > Grant Access**).
   Em _Configurações do projeto > Contas de serviço > Gerar nova chave privada_, baixe o JSON.
2. **ERPNext**: acesse `FCM Settings` e:
   - Ative **Habilitar notificações**.
   - Cole o conteúdo do JSON da conta de serviço em **Service Account JSON**.
   - O **Project ID** é preenchido automaticamente.
   - Clique em **Testar conexão** (botão "Firebase") para validar.

## Uso

### 1) Registrar dispositivo (no app mobile)

```
POST /api/method/erpnext_fcm.api.register_device
Content-Type: application/json
Authorization: token <api_key>:<api_secret>
```

```json
{
  "token": "fcm_registration_token",
  "device_type": "Android",
  "app_version": "1.0.0"
}
```

Para remover: `POST /api/method/erpnext_fcm.api.unregister_device` com `{ "token": "..." }`.

### 2) Enviar notificação

```
POST /api/method/erpnext_fcm.api.send_notification
```

```json
{
  "recipients": "admin", // ou ["user1","user2"] ou "*" para todos
  "title": "Pedido aprovado",
  "body": "O pedido SAL-2026-0001 foi aprovado.",
  "data": { "doctype": "Sales Order", "name": "SAL-2026-0001" },
  "enqueue": false
}
```

### 3) Enviar por evento automático (sem código)

No `FCM Settings`, em **Regras de Notificação**, adicione uma linha:

| Campo                 | Exemplo                                                                               |
| :-------------------- | :------------------------------------------------------------------------------------ |
| DocType               | `Sales Invoice`                                                                       |
| Evento                | `on_submit`                                                                           |
| Campo do destinatário | _(vazio usa o `owner`)_                                                               |
| Título (Jinja)        | `Fatura {{ doc.name }} aprovada`                                                      |
| Mensagem (Jinja)      | `Olá, a fatura de {{ doc.customer }} no valor de {{ doc.grand_total }} foi aprovada.` |
| Dados extras (JSON)   | `{"doctype": "{{ doc.doctype }}", "name": "{{ doc.name }}"}`                          |

### 4) Chamada programática (Server Script / Python)

```python
from erpnext_fcm import services

services.send_to_user(
    user="admin",
    title="Relatório pronto",
    body="Seu relatório foi gerado.",
    data={"link": "/app/report/x"},
    enqueue=True,
)
```

## Estrutura

```
erpnext_fcm/
├── hooks.py            # doc_events, scheduler_events, app meta
├── api.py              # endpoints whitelisted (dispositivo + envio + teste)
├── services.py         # orquestracao de envio + log + tratamento de token invalido
├── methods.py          # motor de regras de evento (Jinja)
├── scheduler.py        # reenvio e limpeza agendada
├── firebase/client.py  # cliente FCM v1 (OAuth2 + HTTP v1)
└── fcm_notifications/doctype/
    ├── fcm_settings/           # Single de configuracao
    ├── fcm_device/             # dispositivo por usuario
    ├── fcm_notification_rule/  # regra filha (evento -> Jinja)
    └── fcm_notification_log/   # historico de envios
```

## Segurança

- **Nunca versionar** o JSON da conta de serviço (já está no `.gitignore`).
- Endpoints exigem usuário autenticado (`register_device`/`unregister_device`/`get_my_devices`
  operam apenas sobre o usuário logado; sem `allow_guest`).
- Credenciais são armazenadas em `FCM Settings` (restrito a `System Manager`) e nunca expostas via API pública.

## Licença

MIT — GL SOLTEC.
