"""Start all A2A agents as background processes."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

from dotenv import load_dotenv

load_dotenv()

AGENTS = ["fila", "cozinha", "preparo", "entrega"]
PORTS = {
    "fila": int(os.getenv("FILA_PORT", "9001")),
    "cozinha": int(os.getenv("COZINHA_PORT", "9002")),
    "preparo": int(os.getenv("PREPARO_PORT", "9003")),
    "entrega": int(os.getenv("ENTREGA_PORT", "9004")),
}


def main():
    processes: list[subprocess.Popen] = []
    print("🥟 Pastel A2A System — Starting all agents...\n")

    for agent in AGENTS:
        proc = subprocess.Popen(  # noqa: S603 — trusted input from AGENTS list
            [sys.executable, "-m", "server.agent_server", agent],
            cwd=os.path.dirname(__file__) or ".",
        )
        processes.append(proc)
        print(f"  ✅ {agent.upper()} agent started (PID: {proc.pid}, port: {PORTS[agent]})")
        time.sleep(0.5)

    print(f"\n🎉 All {len(AGENTS)} agents running!")
    print("Press Ctrl+C to stop all agents.\n")

    def shutdown(sig, frame):
        print("\n🛑 Shutting down all agents...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.wait()
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
