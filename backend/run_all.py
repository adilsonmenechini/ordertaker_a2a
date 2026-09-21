"""Start all A2A agents as threads in a single process.

All agents share the in-memory order store in models.order._orders.
Running in separate processes would isolate state and break the
Fila → Cozinha → Preparo → Entrega flow.
"""

from __future__ import annotations

import os
import signal
import sys
import threading
import time

from dotenv import load_dotenv

load_dotenv()

from server.agent_server import create_app  # noqa: E402

AGENTS = ["fila", "cozinha", "preparo", "entrega"]
PORTS = {
    "fila": int(os.getenv("FILA_PORT", "9001")),
    "cozinha": int(os.getenv("COZINHA_PORT", "9002")),
    "preparo": int(os.getenv("PREPARO_PORT", "9003")),
    "entrega": int(os.getenv("ENTREGA_PORT", "9004")),
}

_threads: list[threading.Thread] = []


def _run_agent(agent: str, port: int) -> None:
    print(f"  ✅ {agent.upper()} agent started (port: {port})")
    app = create_app(agent)
    import uvicorn  # noqa: E402 — lazily imported to avoid cyclic deps
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")  # noqa: S104


def main() -> None:
    print("🥟 Pastel A2A System — Starting all agents...\n")

    for agent in AGENTS:
        t = threading.Thread(
            target=_run_agent,
            args=(agent, PORTS[agent]),
            daemon=True,
        )
        t.start()
        _threads.append(t)
        time.sleep(0.5)

    print(f"\n🎉 All {len(AGENTS)} agents running (shared state)!")
    print("Press Ctrl+C to stop all agents.\n")

    def shutdown(sig: object, frame: object) -> None:  # noqa: A001
        print("\n🛑 Shutting down all agents...")
        for t in _threads:
            t.join(timeout=5)
        print("👋 All agents stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
