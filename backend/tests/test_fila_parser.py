"""Tests for Fila agent order parser — TDD RED phase."""

from models.order import BordaType, SaborType
from server.executors.fila_executor import parse_order_text


class TestParseOrderText:
    def test_simple_order(self):
        _nome, itens = parse_order_text("2 pastéis de carne")
        assert len(itens) == 1
        assert itens[0].sabor == SaborType.CARNE
        assert itens[0].quantidade == 2
        assert itens[0].borda == BordaType.NORMAL

    def test_order_with_borda_catupiry(self):
        _nome, itens = parse_order_text("1 pastel de frango com borda de catupiry")
        assert itens[0].sabor == SaborType.FRANGO
        assert itens[0].borda == BordaType.CATUPIRY

    def test_order_with_borda_queijo(self):
        _nome, itens = parse_order_text("3 pastéis de queijo borda queijo")
        assert itens[0].sabor == SaborType.QUEIJO
        assert itens[0].borda == BordaType.QUEIJO

    def test_order_palmito(self):
        _nome, itens = parse_order_text("1 pastel de palmito")
        assert itens[0].sabor == SaborType.PALMITO

    def test_order_carne_com_queijo(self):
        _nome, itens = parse_order_text("2 pastéis de carne com queijo")
        assert itens[0].sabor == SaborType.CARNE_QUEIJO

    def test_order_with_nome(self):
        nome, _itens = parse_order_text("nome: Maria, 1 pastel de carne")
        assert nome == "Maria"

    def test_default_nome(self):
        nome, _itens = parse_order_text("1 pastel de carne")
        assert nome == "Cliente"

    def test_default_order_when_no_match(self):
        _nome, itens = parse_order_text("quero algo")
        assert len(itens) == 1
        assert itens[0].sabor == SaborType.CARNE

    def test_multiple_sabores(self):
        _nome, itens = parse_order_text("1 pastel de carne e 1 de frango")
        sabores = [i.sabor for i in itens]
        assert SaborType.CARNE in sabores
        assert SaborType.FRANGO in sabores

    def test_quantity_extraction(self):
        _nome, itens = parse_order_text("5 pastéis de carne")
        assert itens[0].quantidade == 5
