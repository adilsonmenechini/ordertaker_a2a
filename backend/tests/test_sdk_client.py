"""Tests for A2A SDK client helpers — TDD RED phase."""

from client.sdk_client import extract_reply_text, get_task_id


class TestExtractReplyText:
    def test_extract_from_artifacts(self):
        result = {"task": {"artifacts": [{"parts": [{"text": "Pedido confirmado"}]}]}}
        assert extract_reply_text(result) == "Pedido confirmado"

    def test_extract_from_status_message(self):
        result = {"task": {"status": {"message": {"parts": [{"text": "Em preparo"}]}}}}
        assert extract_reply_text(result) == "Em preparo"

    def test_extract_from_direct_message(self):
        result = {"message": {"parts": [{"text": "Resposta direta"}]}}
        assert extract_reply_text(result) == "Resposta direta"

    def test_extract_from_parts(self):
        result = {"parts": [{"text": "Texto direto"}]}
        assert extract_reply_text(result) == "Texto direto"

    def test_fallback_to_string(self):
        result = {"unknown": "data"}
        text = extract_reply_text(result)
        assert "unknown" in text


class TestGetTaskId:
    def test_extract_from_task_wrapper(self):
        result = {"task": {"id": "abc-123"}}
        assert get_task_id(result) == "abc-123"

    def test_extract_from_direct_id(self):
        result = {"id": "xyz-789"}
        assert get_task_id(result) == "xyz-789"

    def test_missing_id(self):
        result = {}
        assert get_task_id(result) == ""
