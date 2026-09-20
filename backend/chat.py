"""Terminal chat UI for the pastel ordering system."""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv()

import httpx

from client.sdk_client import AGENT_URLS, discover_agents, extract_reply_text, send_message


async def main():
    print("🥟 Pastelaria Virtual — Chat de Pedidos")
    print("=" * 50)
    print("Exemplo: '2 pastéis de carne com borda de catupiry'")
    print("Comando: 'sair' para encerrar")
    print("=" * 50)

    async with httpx.AsyncClient() as client:
        # Discover agents
        print("\n🔍 Descobrindo agentes...")
        try:
            agents = await discover_agents()
            for a in agents:
                print(f"  ✅ {a.get('name', 'Unknown')} @ {a.get('_base_url')}")
        except Exception as e:
            print(f"  ⚠️ Alguns agentes não estão disponíveis: {e}")
            print("  Execute 'python run_all.py' primeiro!")

        print("\n")

        while True:
            try:
                user_input = input("Você: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 Tchau!")
                break

            if user_input.lower() in ("sair", "exit", "quit"):
                print("👋 Tchau!")
                break
            if not user_input:
                continue

            # Send to fila agent
            print("\n📋 Enviando para a fila...")
            try:
                result = await send_message(
                    client,
                    f"{AGENT_URLS['fila']}/a2a/jsonrpc",
                    user_input,
                )
                reply = extract_reply_text(result)
                print(f"📋 Fila: {reply}")
            except Exception as e:
                print(f"❌ Erro na fila: {e}")
                continue

            # Send to cozinha
            print("\n🍳 Cozinha processando...")
            try:
                result = await send_message(
                    client,
                    f"{AGENT_URLS['cozinha']}/a2a/jsonrpc",
                    "preparar",
                )
                reply = extract_reply_text(result)
                print(f"🍳 Cozinha: {reply}")
            except Exception as e:
                print(f"❌ Erro na cozinha: {e}")

            # Send to preparo
            print("\n📦 Preparo...")
            try:
                result = await send_message(
                    client,
                    f"{AGENT_URLS['preparo']}/a2a/jsonrpc",
                    "embalar",
                    return_immediately=True,
                )
                from client.sdk_client import get_task_id, poll_task

                task_id = get_task_id(result)
                if task_id:
                    reply = await poll_task(
                        client,
                        f"{AGENT_URLS['preparo']}/a2a/jsonrpc",
                        task_id,
                        on_progress=lambda txt: print(f"  📦 {txt}"),
                    )
                    print(f"📦 Preparo: {reply}")
            except Exception as e:
                print(f"❌ Erro no preparo: {e}")

            # Send to entrega
            print("\n🚚 Entrega...")
            try:
                result = await send_message(
                    client,
                    f"{AGENT_URLS['entrega']}/a2a/jsonrpc",
                    "entregar",
                )
                reply = extract_reply_text(result)
                print(f"🚚 Entrega: {reply}")
            except Exception as e:
                print(f"❌ Erro na entrega: {e}")

            print("\n" + "=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
