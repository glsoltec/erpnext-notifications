# Security Policy

## Supported versions

The `version-16` branch supports Frappe Framework and ERPNext 16.x.

## Reporting a vulnerability

Do not open a public issue with credentials, service-account JSON, FCM tokens,
personal data, or exploit details. Send a private report to
`contato@glsoltec.com.br` with:

- affected commit and deployment version;
- impact and affected endpoint or DocType;
- minimal reproduction without secrets or destructive payloads;
- suggested mitigation, if available.

The reporter should redact all credentials and personal data before sending the
report. Rotate any credential that may have been exposed.

## Security controls

- Mutating whitelisted methods require POST.
- Manual notification sending requires System Manager.
- Device tokens are scoped to the logged-in user and masked in list responses.
- Invalid tokens are not retried.
- Firebase service-account files are excluded from Git by `.gitignore`.
- `send_test_notification` is rate-limited per user (3 requests/minute).
- PWA `start_url` and `scope` in the manifest accept only relative paths or HTTPS
  (unsafe values fall back to the default), reducing manifest-based phishing.
- Event dispatch is idempotent within a short window (cache), avoiding duplicate
  pushes for the same document event.
- Runtime dependencies are pinned in `requirements.txt` (generated lockfile).

## Deployment requirements

- Use HTTPS for the ERPNext site.
- Store the Firebase service account outside Git.
- Review FCM Settings permissions before enabling push.
- Rotate the Firebase service account if it is exposed.
