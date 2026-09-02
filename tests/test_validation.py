import unittest

from erpnext_notifications.validation import (
    is_transient_error,
    mask_token,
    next_retry_at,
    normalize_recipients,
    safe_notification_url,
    validate_payload,
)


class TestValidatePayload(unittest.TestCase):
    def test_valid_payload(self):
        out = validate_payload(" Titulo ", " corpo ", image="https://x/img.png", data={"a": 1})
        self.assertEqual(out["title"], "Titulo")
        self.assertEqual(out["body"], "corpo")
        self.assertEqual(out["image"], "https://x/img.png")
        # valores convertidos para string
        self.assertEqual(out["data"], {"a": "1"})

    def test_missing_title(self):
        with self.assertRaises(ValueError):
            validate_payload("", "corpo")

    def test_title_too_long(self):
        with self.assertRaises(ValueError):
            validate_payload("x" * 200, "corpo")

    def test_body_too_long(self):
        with self.assertRaises(ValueError):
            validate_payload("titulo", "x" * 5000)

    def test_rejects_http_image(self):
        out = validate_payload("t", "b", image="http://x/img.png")
        self.assertIsNone(out["image"])

    def test_rejects_nested_data(self):
        with self.assertRaises(ValueError):
            validate_payload("t", "b", data={"x": {"nested": 1}})

    def test_data_limits(self):
        with self.assertRaises(ValueError):
            validate_payload("t", "b", data={f"k{i}": "v" for i in range(30)})

    def test_rejects_non_dict_data(self):
        with self.assertRaises(ValueError):
            validate_payload("t", "b", data={"x": []})  # lista aninhada (não aceito)


class TestNormalizeRecipients(unittest.TestCase):
    def test_all(self):
        self.assertEqual(normalize_recipients("*"), ["*"])

    def test_string(self):
        self.assertEqual(normalize_recipients("user@x.com"), ["user@x.com"])

    def test_list_strips_and_filters(self):
        self.assertEqual(normalize_recipients([" a ", "", " b "]), ["a", "b"])

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            normalize_recipients([])

    def test_too_many(self):
        with self.assertRaises(ValueError):
            normalize_recipients([f"u{i}@x.com" for i in range(600)])


class TestSafeUrl(unittest.TestCase):
    def test_https_ok(self):
        self.assertEqual(safe_notification_url("https://glsoltec.com.br/app"), "https://glsoltec.com.br/app")

    def test_relative_ok(self):
        self.assertEqual(safe_notification_url("/app/finance"), "/app/finance")

    def test_http_blocked(self):
        self.assertIsNone(safe_notification_url("http://glsoltec.com.br/app"))

    def test_javascript_blocked(self):
        self.assertIsNone(safe_notification_url("javascript:alert(1)"))

    def test_none(self):
        self.assertIsNone(safe_notification_url(None))


class TestMaskToken(unittest.TestCase):
    def test_masks(self):
        self.assertNotEqual(mask_token("abc:def:ghi-12345678"), "abc:def:ghi-12345678")
        self.assertTrue(mask_token("abc:def:ghi-12345678").endswith("12345678"))

    def test_short(self):
        self.assertEqual(mask_token("abc"), "…")


class TestRetry(unittest.TestCase):
    def test_next_retry_backoff(self):
        from datetime import datetime

        base = datetime(2026, 1, 1, 12, 0, 0)
        r1 = next_retry_at(1, base)
        r3 = next_retry_at(3, base)
        self.assertGreater(r3, r1)

    def test_transient(self):
        self.assertTrue(is_transient_error(503))
        self.assertFalse(is_transient_error(400))


if __name__ == "__main__":
    unittest.main()