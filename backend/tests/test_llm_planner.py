"""Tests for LLM planner with deterministic fallback — TDD RED phase."""

from unittest.mock import MagicMock, patch

from client.llm_planner import plan_deterministic, plan_order, plan_with_llm


class TestPlanDeterministic:
    def test_returns_order_data(self):
        result = plan_deterministic("2 pastéis de carne com borda de catupiry")
        assert "nome" in result
        assert "itens" in result
        assert len(result["itens"]) == 1

    def test_parses_sabor(self):
        result = plan_deterministic("1 pastel de frango")
        assert result["itens"][0]["sabor"] == "frango"

    def test_parses_quantidade(self):
        result = plan_deterministic("3 pastéis de queijo")
        assert result["itens"][0]["quantidade"] == 3

    def test_parses_borda(self):
        result = plan_deterministic("1 pastel de carne com borda de catupiry")
        assert result["itens"][0]["borda"] == "catupiry"


class TestPlanOrder:
    @patch("client.llm_planner.plan_with_llm")
    def test_uses_llm_when_available(self, mock_llm):
        mock_llm.return_value = {"nome": "LLM", "itens": [{"sabor": "carne"}]}
        _response, data = plan_order("2 carnes")
        assert data["nome"] == "LLM"
        mock_llm.assert_called_once()

    @patch("client.llm_planner.plan_with_llm")
    def test_fallback_to_deterministic(self, mock_llm):
        mock_llm.return_value = None
        response, data = plan_order("2 pastéis de carne")
        assert data["nome"] == "Cliente"
        assert "carne" in response

    @patch("client.llm_planner.plan_with_llm")
    def test_llm_returns_empty_response(self, mock_llm):
        mock_llm.return_value = {}
        _response, data = plan_order("1 frango")
        # Empty dict is falsy, should fallback
        assert data["nome"] == "Cliente"


class TestPlanWithLLMKeyCleaning:
    @patch("client.llm_planner.OpenAI")
    def test_plan_with_llm_strips_unicode_from_key(self, mock_openai_class):
        """LLM planner must clean non-ASCII chars from API key."""
        import os
        os.environ["OPENAI_API_KEY"] = "sk-test\u00f3key"  # contains ó
        os.environ["OPENAI_BASE_URL"] = "http://localhost:20128/v1"

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"nome": "Test", "itens": []}'))]
        )

        plan_with_llm("test order")

        # Verify OpenAI was called with CLEANED key (no ó)
        call_kwargs = mock_openai_class.call_args[1]
        expected_key = "sk-testkey"
        assert "\u00f3" not in call_kwargs["api_key"], "API key should not contain ó"
        assert call_kwargs["api_key"] == expected_key, (
            f"Expected '{expected_key}', got '{call_kwargs['api_key']}'"
        )
