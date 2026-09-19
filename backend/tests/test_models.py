"""Tests for order data models — TDD RED phase."""

from models.order import (
    BordaType,
    Order,
    OrderStatus,
    PastelItem,
    SaborType,
    create_order,
    get_order,
    list_orders,
)


class TestOrderStatus:
    def test_order_status_enum_values(self):
        assert OrderStatus.PEDIDO.value == "pedido"
        assert OrderStatus.FILA.value == "fila"
        assert OrderStatus.COZINHA.value == "cozinha"
        assert OrderStatus.PREPARO.value == "preparo"
        assert OrderStatus.ENTREGA.value == "entrega"
        assert OrderStatus.CONCLUIDO.value == "concluido"

    def test_order_status_is_string(self):
        assert isinstance(OrderStatus.PEDIDO, str)


class TestPastelItem:
    def test_create_item_with_defaults(self):
        item = PastelItem(sabor=SaborType.CARNE)
        assert item.sabor == SaborType.CARNE
        assert item.quantidade == 1
        assert item.borda == BordaType.NORMAL
        assert item.observacoes == ""

    def test_create_item_custom(self):
        item = PastelItem(
            sabor=SaborType.FRANGO,
            quantidade=3,
            borda=BordaType.CATUPIRY,
            observacoes="sem cebola",
        )
        assert item.sabor == SaborType.FRANGO
        assert item.quantidade == 3
        assert item.borda == BordaType.CATUPIRY
        assert item.observacoes == "sem cebola"


class TestOrder:
    def test_create_order_generates_id(self):
        order = Order()
        assert order.id is not None
        assert len(order.id) == 8

    def test_create_order_default_status(self):
        order = Order()
        assert order.status == OrderStatus.PEDIDO

    def test_advance_status(self):
        order = Order()
        assert order.status == OrderStatus.PEDIDO
        order.advance()
        assert order.status == OrderStatus.FILA
        order.advance()
        assert order.status == OrderStatus.COZINHA
        order.advance()
        assert order.status == OrderStatus.PREPARO
        order.advance()
        assert order.status == OrderStatus.ENTREGA
        order.advance()
        assert order.status == OrderStatus.CONCLUIDO

    def test_advance_beyond_completed_stays(self):
        order = Order(status=OrderStatus.CONCLUIDO)
        result = order.advance()
        assert result == OrderStatus.CONCLUIDO

    def test_timeline_records_timestamps(self):
        order = Order()
        order.timeline["pedido"] = "2024-01-01T00:00:00"
        assert "pedido" in order.timeline

    def test_to_summary(self):
        item = PastelItem(sabor=SaborType.CARNE, quantidade=2, borda=BordaType.NORMAL)
        order = Order(id="test1234", itens=[item], status=OrderStatus.FILA)
        summary = order.to_summary()
        assert "test1234" in summary
        assert "carne" in summary
        assert "fila" in summary


class TestOrderStore:
    def setup_method(self):
        """Clear store before each test."""
        from models import order as order_module

        order_module._orders.clear()

    def test_create_order_adds_to_store(self):
        item = PastelItem(sabor=SaborType.CARNE)
        order = create_order("Teste", [item])
        assert order.cliente_nome == "Teste"
        assert len(order.itens) == 1
        assert order.id in [o.id for o in list_orders()]

    def test_get_order(self):
        item = PastelItem(sabor=SaborType.FRANGO)
        order = create_order("Maria", [item])
        retrieved = get_order(order.id)
        assert retrieved is not None
        assert retrieved.cliente_nome == "Maria"

    def test_get_order_not_found(self):
        assert get_order("nonexistent") is None

    def test_list_orders(self):
        assert len(list_orders()) == 0
        create_order("A", [PastelItem(sabor=SaborType.CARNE)])
        create_order("B", [PastelItem(sabor=SaborType.QUEIJO)])
        assert len(list_orders()) == 2

    def test_create_order_sets_timeline(self):
        order = create_order("Teste", [PastelItem(sabor=SaborType.CARNE)])
        assert "pedido" in order.timeline
