# Marketplace Readiness

## Scope

This document records the technical checks for publishing `erpnext_notifications`
on the Frappe Marketplace. Marketplace approval is controlled by Frappe and is
not guaranteed by this repository.

## Current status

| Check                        | Status                        | Evidence or action                                                              |
| ---------------------------- | ----------------------------- | ------------------------------------------------------------------------------- |
| Public GitHub repository     | Ready                         | `https://github.com/glsoltec/erpnext-notifications`                             |
| Target branch                | Ready                         | `version-16`                                                                    |
| Frappe/ERPNext compatibility | Ready for review              | `pyproject.toml` declares 16.x; validate against the Marketplace target version |
| App metadata                 | Ready for review              | `hooks.py`, `pyproject.toml`                                                    |
| Open-source license          | Ready                         | `LICENSE` and `license.txt`, MIT                                                |
| Package manifest             | Ready                         | `MANIFEST.in`, `modules.txt`, `patches.txt`                                     |
| Installation documentation   | Ready                         | `README.md`                                                                     |
| Security policy              | Ready                         | `SECURITY.md`                                                                   |
| Automated CI                 | Present, not locally executed | `.github/workflows/ci.yml`; confirm all checks pass on GitHub                   |
| Frappe integration test      | Pending                       | Execute on a clean Frappe/ERPNext 16 site                                       |
| Firebase end-to-end test     | Pending                       | Configure a test Firebase project and browser/device                            |
| Marketplace profile          | Pending                       | Publisher account, icon, screenshots, description and submission                |

## Release checklist

1. Create a GitHub release/tag matching the app version.
2. Confirm the tag points to the intended `version-16` commit.
3. Run CI and retain the reports as release evidence.
4. Install on a clean Frappe/ERPNext 16 site.
5. Test migration, uninstall backup procedure and reinstallation.
6. Test web push with HTTPS, a supported browser and a test Firebase project.
7. Test Notification Log relay, manual notification and automatic rules.
8. Verify permission boundaries with Guest, regular user and System Manager.
9. Confirm no credential, FCM token or personal data is in the release artifact.
10. Complete the Marketplace profile and submit for review.

## Known limitations

- The repository provides web/PWA registration and server-side FCM delivery;
  it does not contain a native Android or iOS application.
- A native client must register its FCM token using the documented API.
- The service worker loads Firebase compatibility SDKs with `importScripts`;
  browser SRI is not available for that API. The SDK version is fixed in code.
- Frappe/ERPNext site configuration, Firebase billing, quota and browser support
  remain deployment responsibilities.
