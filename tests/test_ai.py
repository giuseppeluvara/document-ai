"""Meaningful extraction tests with no downloaded model or network dependency."""

import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from documents.services import ai


FIELD = {"key": "parti", "label": "Parti", "description": "Parti del contratto", "type": "text"}
SEGMENT = {"id": "p1", "text": "Il contratto è stipulato con Alfa S.r.l. per euro 1.200,50 il 23 ottobre 2026."}


def raw(value, quote=None, key="parti", segment_id="p1"):
    return {"key": key, "value": value,
            "evidence": [{"segment_id": segment_id, "quote": quote}] if quote is not None else []}


def extract(segments=None, fields=None, **kwargs):
    return ai.run_extraction(
        segments if segments is not None else [SEGMENT], fields or [FIELD],
        endpoint=kwargs.pop("endpoint", "http://127.0.0.1:8080/v1"),
        model="document-ai", **kwargs)


class GroundingTests(unittest.TestCase):
    @patch.object(ai, "_request_json")
    def test_accepts_value_with_matching_quote_and_source(self, request_json):
        request_json.return_value = [raw("Alfa S.r.l.", "stipulato con Alfa S.r.l.")]
        result = extract()
        self.assertEqual(result["fields"][0]["value"], "Alfa S.r.l.")
        self.assertEqual(result["fields"][0]["status"], "found")
        self.assertEqual(result["fields"][0]["evidence"][0]["segment_id"], "p1")

    @patch.object(ai, "_request_json")
    def test_rejects_hallucinated_value_with_real_but_unrelated_quote(self, request_json):
        request_json.return_value = [raw("Beta S.p.A.", "stipulato con Alfa S.r.l.")]
        field = extract()["fields"][0]
        self.assertIsNone(field["value"])
        self.assertEqual(field["status"], "not_found")
        self.assertTrue(field["warnings"])

    @patch.object(ai, "_request_json")
    def test_rejects_invented_quote_and_wrong_segment(self, request_json):
        for entry in [raw("Beta", "Beta"), raw("Alfa", "Alfa", segment_id="p999")]:
            request_json.return_value = [entry]
            self.assertIsNone(extract()["fields"][0]["value"])

    @patch.object(ai, "_request_json")
    def test_whitespace_differences_are_allowed(self, request_json):
        request_json.return_value = [raw("Alfa S.r.l.", "Alfa\n  S.r.l.")]
        self.assertEqual(extract()["fields"][0]["value"], "Alfa S.r.l.")

    @patch.object(ai, "_request_json")
    def test_unknown_and_missing_fields_are_explicit(self, request_json):
        request_json.return_value = [raw("x", "x", key="other"), {"key": []}]
        result = extract()
        self.assertTrue(result["warnings"])
        self.assertTrue(result["fields"][0]["warnings"])
        self.assertIsNone(result["fields"][0]["value"])

    @patch.object(ai, "_request_json")
    def test_number_and_italian_date_normalization(self, request_json):
        fields = [{"key": "amount", "label": "Importo", "type": "number"},
                  {"key": "date", "label": "Data", "type": "date"}]
        request_json.return_value = [
            raw(1200.50, "euro 1.200,50", key="amount"),
            raw("2026-10-23", "il 23 ottobre 2026", key="date"),
        ]
        result = extract(fields=fields)
        self.assertEqual([f["value"] for f in result["fields"]], [1200.50, "2026-10-23"])

    @patch.object(ai, "_request_json")
    def test_invalid_types_and_uncovered_list_items_are_rejected(self, request_json):
        for kind, value, quote in [
            ("number", True, "1.200,50"),
            ("number", float("nan"), "1.200,50"),
            ("date", "2026-02-30", "23 ottobre 2026"),
            ("list", ["Alfa S.r.l.", "Beta"], "Alfa S.r.l."),
        ]:
            request_json.return_value = [raw(value, quote)]
            self.assertIsNone(extract(fields=[{**FIELD, "type": kind}])["fields"][0]["value"])


class ChunkTests(unittest.TestCase):
    @patch.object(ai, "_request_json")
    def test_all_long_text_is_processed_and_boundary_overlap_exists(self, request_json):
        text = "a" * 700 + "Ultima clausola Alfa S.r.l."
        request_json.side_effect = lambda url, model, fields, chunk, timeout, max_tokens: (
            [raw("Alfa S.r.l.", "Ultima clausola Alfa S.r.l.")]
            if any("Ultima clausola" in p["text"] for p in chunk) else [raw(None)])
        result = extract(segments=[{"id": "p1", "text": text}], context_chars=500)
        self.assertEqual(result["fields"][0]["value"], "Alfa S.r.l.")
        chunks = [call.args[3][0]["text"] for call in request_json.call_args_list]
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0][-62:], chunks[1][:62])
        self.assertTrue(all(len(chunk) <= 500 for chunk in chunks))
        self.assertEqual(chunks[0] + chunks[1][62:], text)

    @patch.object(ai, "_request_json")
    def test_conflicting_singular_values_require_review(self, request_json):
        request_json.side_effect = [
            [raw("Alfa", "Alfa", segment_id="p1")],
            [raw("Beta", "Beta", segment_id="p2")],
        ]
        result = extract(segments=[{"id": "p1", "text": "Alfa " + "a" * 450},
                                   {"id": "p2", "text": "Beta " + "b" * 450}], context_chars=500)
        field = result["fields"][0]
        self.assertIsNone(field["value"])
        self.assertEqual(len(field["evidence"]), 2)
        self.assertIn("Valori differenti", field["warnings"][0])

    @patch.object(ai, "_request_json")
    def test_lists_merge_without_duplicates(self, request_json):
        request_json.side_effect = [[raw(["Alfa"], "Alfa")],
                                    [raw(["Beta", "Alfa"], "Beta e Alfa", segment_id="p2")]]
        result = extract(segments=[{"id": "p1", "text": "Alfa " + "a" * 450},
                                   {"id": "p2", "text": "Beta e Alfa " + "b" * 450}],
                         fields=[{**FIELD, "type": "list"}], context_chars=500)
        self.assertEqual(result["fields"][0]["value"], ["Alfa", "Beta"])

    @patch.object(ai, "_request_json")
    def test_quote_elsewhere_in_document_is_not_accepted(self, request_json):
        request_json.side_effect = [[raw("Beta", "Beta", segment_id="p2")], [raw(None)]]
        result = extract(segments=[{"id": "p1", "text": "Alfa " + "a" * 450},
                                   {"id": "p2", "text": "Beta " + "b" * 450}], context_chars=500)
        self.assertIsNone(result["fields"][0]["value"])

    @patch.object(ai, "_request_json")
    def test_empty_document_does_not_call_runtime(self, request_json):
        result = extract(segments=[])
        request_json.assert_not_called()
        self.assertTrue(result["warnings"])


class TransportTests(unittest.TestCase):
    def test_only_numeric_loopback_or_localhost_http_are_allowed(self):
        for endpoint in ["https://127.0.0.1:8080", "http://example.com", "http://10.0.0.1:8080",
                         "http://127.0.0.1:8080/path", "http://user:secret@localhost:8080",
                         "http://127.0.0.1:8080?token=x"]:
            with self.subTest(endpoint=endpoint), self.assertRaises(ai.AIError):
                extract(endpoint=endpoint)
        self.assertEqual(ai._endpoint_url("http://localhost:8080/v1"), "http://127.0.0.1:8080/v1/chat/completions")
        self.assertEqual(ai._endpoint_url("http://[::1]:8080"), "http://[::1]:8080/v1/chat/completions")

    @patch.object(ai.request, "build_opener")
    def test_request_disables_proxy_redirects_and_thinking(self, build_opener):
        envelope = {"choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps({"fields": [raw("Alfa", "Alfa")]})}}]}
        build_opener.return_value.open.return_value.__enter__.return_value.read.return_value = json.dumps(envelope).encode()
        result = extract()
        self.assertEqual(result["fields"][0]["value"], "Alfa")
        handlers = build_opener.call_args.args
        self.assertEqual(handlers[0].proxies, {})
        self.assertIsInstance(handlers[1], ai._NoRedirect)
        req = build_opener.return_value.open.call_args.args[0]
        body = json.loads(req.data)
        self.assertFalse(body["chat_template_kwargs"]["enable_thinking"])
        self.assertEqual(body["response_format"]["type"], "json_object")
        self.assertIn("schema", body["response_format"])

    @patch.object(ai.request, "build_opener")
    def test_runtime_unavailable_is_safe_and_actionable(self, build_opener):
        build_opener.return_value.open.side_effect = URLError("private server traceback")
        with self.assertRaisesRegex(ai.AIError, "Avviare llama-server") as caught:
            extract()
        self.assertNotIn("private", str(caught.exception))

    @patch.object(ai.request, "build_opener")
    def test_redirect_is_not_followed(self, build_opener):
        build_opener.return_value.open.side_effect = HTTPError("local", 302, "Moved", {}, io.BytesIO())
        with self.assertRaisesRegex(ai.AIError, "reindirizzamento"):
            extract()

    @patch.object(ai.request, "build_opener")
    def test_truncated_or_invalid_output_is_not_accepted(self, build_opener):
        response = build_opener.return_value.open.return_value.__enter__.return_value
        for payload in [
            b"not json",
            json.dumps({"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]}).encode(),
            json.dumps({"choices": [{"message": {"content": "```json {} ```"}}]}).encode(),
        ]:
            response.read.return_value = payload
            with self.assertRaises(ai.AIError):
                extract()

    def test_redirect_handler_refuses_new_request(self):
        self.assertIsNone(ai._NoRedirect().redirect_request(None, None, 302, "Moved", {}, "https://example.com"))


if __name__ == "__main__":
    unittest.main()
