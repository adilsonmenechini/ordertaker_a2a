"""Tests for backend A2A agents — executor integration and Role enum correctness."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from a2a.types import Message, Part, Role


class TestRoleEnum:
    """Verify A2A SDK Role enum usage matches the installed SDK version."""

    def test_role_agent_exists(self):
        """Executors must use Role.ROLE_AGENT, not Role.agent."""
        assert hasattr(Role, "ROLE_AGENT")

    def test_role_agent_value(self):
        # Protobuf enums return int directly
        assert Role.ROLE_AGENT == 2

    def test_role_user_value(self):
        assert Role.ROLE_USER == 1


class TestFilaExecutor:
    @pytest.mark.asyncio
    async def test_fila_executor_enqueues_reply(self):
        """FilaExecutor must enqueue a Message with Role.ROLE_AGENT."""
        from server.executors.fila_executor import FilaExecutor

        executor = FilaExecutor()
        context = MagicMock()
        context.message = Message(
            role=Role.ROLE_USER,
            parts=[Part(text="2 pastéis de carne com borda de catupiry")],
        )
        event_queue = AsyncMock()

        await executor.execute(context, event_queue)

        event_queue.enqueue_event.assert_called_once()
        enqueued = event_queue.enqueue_event.call_args[0][0]
        assert isinstance(enqueued, Message)
        assert enqueued.role == Role.ROLE_AGENT
        assert any(p.text and "carne" in p.text for p in enqueued.parts)

    @pytest.mark.asyncio
    async def test_fila_executor_default_order(self):
        """When no known sabor matched, default to carne."""
        from server.executors.fila_executor import FilaExecutor

        executor = FilaExecutor()
        context = MagicMock()
        context.message = Message(
            role=Role.ROLE_USER,
            parts=[Part(text="quero algo diferente")],
        )
        event_queue = AsyncMock()

        await executor.execute(context, event_queue)

        enqueued = event_queue.enqueue_event.call_args[0][0]
        assert any(p.text and "carne" in p.text for p in enqueued.parts)


class TestCozinhaExecutor:
    @pytest.mark.asyncio
    async def test_cozinha_executor_no_active_orders(self):
        """When no orders in fila/cozinha, return empty message."""
        from models.order import _orders
        from server.executors.cozinha_executor import CozinhaExecutor

        _orders.clear()
        executor = CozinhaExecutor()
        context = MagicMock()
        context.message = Message(
            role=Role.ROLE_USER,
            parts=[Part(text="preparar")],
        )
        event_queue = AsyncMock()

        await executor.execute(context, event_queue)

        enqueued = event_queue.enqueue_event.call_args[0][0]
        assert any(
            p.text and "Nenhum pedido" in p.text for p in enqueued.parts
        )

    @pytest.mark.asyncio
    async def test_cozinha_executor_processes_order(self):
        """When order is in FILA, advance to COZINHA and send steps."""
        from models.order import OrderStatus, PastelItem, SaborType, _orders, create_order
        from server.executors.cozinha_executor import CozinhaExecutor

        _orders.clear()
        order = create_order("Teste", [PastelItem(sabor=SaborType.CARNE)])
        order.advance()  # PEDIDO -> FILA
        assert order.status == OrderStatus.FILA

        executor = CozinhaExecutor()
        context = MagicMock()
        context.message = Message(
            role=Role.ROLE_USER,
            parts=[Part(text="preparar")],
        )
        event_queue = AsyncMock()

        await executor.execute(context, event_queue)

        # Should have sent a single aggregated message (steps + final)
        assert event_queue.enqueue_event.call_count == 1
        enqueued = event_queue.enqueue_event.call_args[0][0]
        assert any(p.text and "Aquecendo" in p.text for p in enqueued.parts)
        assert any(p.text and "saiu da cozinha" in p.text for p in enqueued.parts)
        # Order should have advanced to PREPARO
        assert order.status == OrderStatus.PREPARO


class TestPreparoExecutor:
    @pytest.mark.asyncio
    async def test_preparo_executor_no_active_orders(self):
        """When no orders in preparo, return empty message."""
        from models.order import _orders
        from server.executors.preparo_executor import PreparoExecutor

        _orders.clear()
        executor = PreparoExecutor()
        context = MagicMock()
        context.message = Message(
            role=Role.ROLE_USER,
            parts=[Part(text="embalar")],
        )
        event_queue = AsyncMock()

        await executor.execute(context, event_queue)

        enqueued = event_queue.enqueue_event.call_args[0][0]
        assert any(
            p.text and "Nenhum pedido" in p.text for p in enqueued.parts
        )

    @pytest.mark.asyncio
    async def test_preparo_executor_processes_order(self):
        """When order is in PREPARO, advance to ENTREGA."""
        from models.order import (
            OrderStatus,
            PastelItem,
            SaborType,
            _orders,
            create_order,
        )
        from server.executors.preparo_executor import PreparoExecutor

        _orders.clear()
        order = create_order("Teste", [PastelItem(sabor=SaborType.FRANGO)])
        order.advance()  # PEDIDO -> FILA
        order.advance()  # FILA -> COZINHA
        order.advance()  # COZINHA -> PREPARO
        assert order.status == OrderStatus.PREPARO

        executor = PreparoExecutor()
        context = MagicMock()
        context.message = Message(
            role=Role.ROLE_USER,
            parts=[Part(text="embalar")],
        )
        event_queue = AsyncMock()

        await executor.execute(context, event_queue)

        # Should have sent a single aggregated message (steps + final)
        assert event_queue.enqueue_event.call_count == 1
        enqueued = event_queue.enqueue_event.call_args[0][0]
        assert any(p.text and "Enfatando" in p.text for p in enqueued.parts)
        assert any(p.text and "saiu para entrega" in p.text for p in enqueued.parts)
        assert order.status == OrderStatus.ENTREGA


class TestEntregaExecutor:
    @pytest.mark.asyncio
    async def test_entrega_executor_no_active_orders(self):
        """When no orders in entrega, return empty message."""
        from models.order import _orders
        from server.executors.entrega_executor import EntregaExecutor

        _orders.clear()
        executor = EntregaExecutor()
        context = MagicMock()
        event_queue = AsyncMock()

        await executor.execute(context, event_queue)

        enqueued = event_queue.enqueue_event.call_args[0][0]
        assert any(
            p.text and "Nenhum pedido" in p.text for p in enqueued.parts
        )

    @pytest.mark.asyncio
    async def test_entrega_executor_processes_order(self):
        """When order is in ENTREGA, advance to CONCLUIDO."""
        from models.order import (
            OrderStatus,
            PastelItem,
            SaborType,
            _orders,
            create_order,
        )
        from server.executors.entrega_executor import EntregaExecutor

        _orders.clear()
        order = create_order("João", [PastelItem(sabor=SaborType.QUEIJO)])
        order.advance()  # PEDIDO -> FILA
        order.advance()  # FILA -> COZINHA
        order.advance()  # COZINHA -> PREPARO
        order.advance()  # PREPARO -> ENTREGA
        assert order.status == OrderStatus.ENTREGA

        executor = EntregaExecutor()
        event_queue = AsyncMock()

        await executor.execute(MagicMock(), event_queue)

        enqueued = event_queue.enqueue_event.call_args[0][0]
        assert enqueued.role == Role.ROLE_AGENT
        assert any(p.text and "entregue" in p.text for p in enqueued.parts)
        assert order.status == OrderStatus.CONCLUIDO
