"""Regression checks for publication redaction; only synthetic secrets are used."""

import copy
import unittest

from anonymize_workflows import anonymize


class AnonymizationTests(unittest.TestCase):
    def test_private_fields_and_embedded_values_are_removed(self):
        workflow = {
            "id": "private-workflow-id", "meta": {"instanceId": "private-instance"},
            "staticData": {"private": True}, "pinData": {"output": "private"},
            "active": True, "tags": [{"name": "personal"}],
            "nodes": [
                {"id": "telegram", "type": "n8n-nodes-base.telegram",
                 "credentials": {"telegramApi": {"id": "private-credential"}},
                 "webhookId": "private-webhook", "notes": "private annotation",
                 "parameters": {"chatId": "123456789", "password": "private-password",
                                "headers": [{"name": "Authorization", "value": "private-header"}],
                                "url": "https://example.org/?token=private-query",
                                "tokenText": "123456789:" + "A" * 35,
                                "email": "person@private.example",
                                "key": "-----BEGIN PRIVATE KEY-----\nprivate-key\n-----END PRIVATE KEY-----"}},
                {"id": "note", "type": "n8n-nodes-base.stickyNote",
                 "parameters": {"content": r"C:\Users\private-user\backup", "width": 500}},
            ], "connections": {},
        }
        original = copy.deepcopy(workflow)
        result = anonymize(workflow)
        serialized = str(result)
        for secret in ("private-workflow-id", "private-instance", "private-credential",
                       "private-webhook", "private annotation", "123456789",
                       "private-password", "private-header", "private-query",
                       "person@private.example", "private-key", "private-user"):
            self.assertNotIn(secret, serialized)
        self.assertEqual(workflow, original)
        self.assertFalse(result["active"])
        self.assertEqual(result["pinData"], {})
        self.assertEqual(result, anonymize(result))

    def test_processing_code_ids_and_connections_are_preserved(self):
        workflow = {
            "nodes": [{"id": "code-1", "name": "Process", "type": "n8n-nodes-base.code",
                       "parameters": {"jsCode": "return $input.all().map(x => x);"}}],
            "connections": {"Process": {"main": [[]]}},
        }
        result = anonymize(workflow)
        self.assertEqual(result["nodes"], workflow["nodes"])
        self.assertEqual(result["connections"], workflow["connections"])

    def test_invalid_export_is_rejected(self):
        for value in ([], {}, {"nodes": "invalid"}):
            with self.assertRaises(ValueError):
                anonymize(value)


if __name__ == "__main__":
    unittest.main()
