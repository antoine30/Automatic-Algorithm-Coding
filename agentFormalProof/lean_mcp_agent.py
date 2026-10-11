"""
Agent IA qui écrit et fait évoluer du code Lean prouvé, via des serveurs MCP.

Usage :
  pip install anthropic mcp
  export ANTHROPIC_API_KEY=...
  python lean_mcp_agent.py /chemin/vers/projet_lean

Le projet Lean doit contenir task.md, Check.lean (spec figée) et être un dépôt git.
Pour faire évoluer le code : modifiez task.md et Check.lean, puis relancez l'agent.
"""
import asyncio
import os
import subprocess
import sys
from contextlib import AsyncExitStack
from pathlib import Path

import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MODEL = "claude-sonnet-5"
MAX_STEPS = 40
HERE = Path(__file__).resolve().parent

SYSTEM = """You are a Lean 4 engineer. Your goal: make the frozen spec Check.lean hold
by writing Solution.lean (everything in `namespace Solution`).
Workflow: call read_task, write a solution, call check, read the errors, use run_snippet
to inspect goals or find lemmas, fix, and repeat until check returns PROVED.
If a Solution.lean already exists, adapt it rather than rewriting it.
Never use sorry, admit, axiom, native_decide or unsafe: they are rejected."""


def servers(project: Path) -> dict[str, StdioServerParameters]:
    env = dict(os.environ)
    return {
        "verifier": StdioServerParameters(
            command=sys.executable,
            args=[str(HERE / "lean_verifier_server.py")],
            cwd=str(project), env=env),
        # Optionnel : outils riches (état des buts, recherche de lemmes...) via le LSP de Lean
        # "lsp": StdioServerParameters(command="uvx", args=["lean-lsp-mcp"],
        #                              cwd=str(project), env=env),
    }


def text_of(result) -> str:
    return "\n".join(c.text for c in result.content if c.type == "text")


async def run_agent(project: Path) -> bool:
    client = anthropic.AsyncAnthropic()
    async with AsyncExitStack() as stack:
        # 1. Connexion aux serveurs MCP et récupération de leurs outils
        routes, tools = {}, []
        for server_name, params in servers(project).items():
            read, write = await stack.enter_async_context(stdio_client(params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            for tool in (await session.list_tools()).tools:
                full_name = f"{server_name}__{tool.name}"
                routes[full_name] = (session, tool.name)
                tools.append({"name": full_name,
                              "description": tool.description or "",
                              "input_schema": tool.inputSchema})

        # 2. Boucle agentique : Claude appelle les outils jusqu'à ce qu'il s'arrête
        messages = [{"role": "user", "content": "Make the frozen spec hold. Start with read_task."}]
        for step in range(1, MAX_STEPS + 1):
            response = await client.messages.create(
                model=MODEL, max_tokens=8000, system=SYSTEM,
                tools=tools, messages=messages)
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                break

            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                session, tool_name = routes[block.name]
                print(f"[{step}] {block.name}")
                result = await session.call_tool(tool_name, block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": text_of(result)[-8000:],
                                "is_error": bool(result.isError)})
            messages.append({"role": "user", "content": results})

        # 3. Verdict final : on ne croit pas l'agent sur parole, on vérifie nous-mêmes
        session, tool_name = routes["verifier__check"]
        verdict = text_of(await session.call_tool(tool_name, {}))

    git = lambda *args: subprocess.run(["git", *args], cwd=project, capture_output=True)
    if verdict.startswith("PROVED"):
        git("add", "Solution.lean")
        git("commit", "-m", "Agent: spec proved")
        print("PROVED: Solution.lean committed.")
        return True

    git("checkout", "--", "Solution.lean")  # restaure la dernière version prouvée
    print("Not proved, last proved version restored. Human review needed.\n" + verdict)
    return False


if __name__ == "__main__":
    project = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    sys.exit(0 if asyncio.run(run_agent(project)) else 1)
