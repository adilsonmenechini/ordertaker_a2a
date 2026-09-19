"""Tests for LLM planner with deterministic fallback — TDD RED phase."""

from unittest.mock import patch

from client.llm_planner import plan_deterministic, plan_order


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
