#!/usr/bin/env python3
"""
Smoke-test client for the STM32 Template MCP server.

Drives stm32_mcp_server.py over stdio exactly like a real MCP client (the same
transport Claude Desktop / Claude Code use), to verify the server starts, lists
its tools, reports a healthy toolchain, and can BUILD the scaffold project.

Usage:
    python smoke_test.py                # build the template scaffold (make)
    python smoke_test.py --system cmake # build via cmake+ninja instead
    python smoke_test.py --no-build     # only handshake + get_config + list

Deliberately does NOT flash (no programmer assumed attached).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

THIS_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = THIS_DIR.parent
SERVER = THIS_DIR / "stm32_mcp_server.py"


def _payload(result) -> dict:
    """Pull the JSON dict a FastMCP tool returned, from either structured
    content or the first text block."""
    if getattr(result, "structuredContent", None):
        sc = result.structuredContent
        # FastMCP wraps bare return values under "result"
        return sc.get("result", sc) if isinstance(sc, dict) else sc
    for block in getattr(result, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"_raw": text}
    return {}


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", default="make", choices=["make", "cmake"])
    ap.add_argument("--project-dir", default=str(TEMPLATE_DIR))
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--clean-first", action="store_true")
    args = ap.parse_args()

    # Full environment so the server (and the build subprocess it spawns) has a
    # normal PATH, plus the two overrides the server understands.
    env = dict(os.environ)
    env["STM32_TEMPLATE_DIR"] = str(TEMPLATE_DIR).replace("\\", "/")

    params = StdioServerParameters(
        command=sys.executable, args=[str(SERVER)], env=env, cwd=str(THIS_DIR)
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("== initialize OK ==")

            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print(f"== tools ({len(names)}): {', '.join(names)}")

            cfg = _payload(await session.call_tool("get_config", {}))
            tc_ok = cfg.get("toolchain_ok")
            disc = cfg.get("discovered_toolchain", {})
            print(f"== get_config: toolchain_ok={tc_ok}")
            for k in ("gcc_bin", "make_bin", "cmake_bin", "ninja_bin", "programmer_cli"):
                print(f"     {k:14}= {disc.get(k)}")
            if not tc_ok:
                print("!! toolchain_ok is False — gcc/make/programmer not all found.")

            if args.no_build:
                return 0

            print(f"== build (system={args.system}, project_dir={args.project_dir}) ...")
            res = _payload(await session.call_tool(
                "build",
                {"project_dir": args.project_dir, "system": args.system,
                 "clean_first": args.clean_first},
            ))
            print(f"   ok={res.get('ok')} returncode={res.get('returncode')} stage={res.get('stage')}")
            if res.get("error"):
                print(f"   error: {res['error']}")
            tail = (res.get("stdout") or "")[-1500:]
            err = (res.get("stderr") or "")[-3000:]
            if tail:
                print("   --- stdout (tail) ---\n" + tail)
            if err:
                print("   --- stderr (tail) ---\n" + err)
            print(f"   artifacts: {json.dumps(res.get('artifacts', {}), indent=2)}")
            return 0 if res.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
