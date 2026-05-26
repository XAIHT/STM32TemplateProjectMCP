#!/usr/bin/env python3
"""
STM32 Template MCP Server
=========================

An MCP (Model Context Protocol) server that lets an agent spin up, fill, build,
and flash STM32F4 firmware projects from the STM32TemplateProject scaffold —
without ever opening STM32CubeIDE.

Lifecycle exposed to the agent:
    1. create_project   -> copy the template to a new location
    2. write_source     -> drop generated source files into <proj>/project/...
    3. build            -> compile + link + objcopy (make or cmake)  -> .elf/.hex/.bin
    4. flash            -> upload the .bin/.elf to the MCU over ST-LINK
    (+ erase, reset, clean, get_config, discover_toolchain, list_artifacts)

Hardware-in-the-loop (talk to / observe a running board):
    serial_*            -> open a VCP/UART, send commands, read replies
    read_memory /       -> read/write live RAM, peripherals or named symbols over
    write_memory           SWD without resetting the target (mode=HOTPLUG)
    live_memory_*       -> stream variables continuously via a persistent OpenOCD
                           (start/read/stop), without halting the target

Everything is driven by stm32.config.json at the template root, but tool paths
are auto-discovered from the STM32CubeIDE install (robust to IDE version bumps).

Run (stdio transport, the default for desktop/agent integration):
    python stm32_mcp_server.py

Environment overrides:
    STM32_TEMPLATE_DIR   path to STM32TemplateProject   (default: ../ from this file)
    STM32_IDE_ROOT       STM32CubeIDE install root       (default: from config / well-known)
"""

from __future__ import annotations

import collections
import glob
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

# --------------------------------------------------------------------------- #
#  Paths & configuration
# --------------------------------------------------------------------------- #

THIS_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = Path(os.environ.get("STM32_TEMPLATE_DIR", str(THIS_DIR.parent))).resolve()
CONFIG_PATH = TEMPLATE_DIR / "stm32.config.json"

# Folders that must NOT be copied when cloning the template into a new project.
COPY_IGNORE = shutil.ignore_patterns(
    "build", "build-*", "*.log", ".git", "__pycache__", ".venv", "venv"
)


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def _norm(p: Optional[str]) -> Optional[str]:
    return p.replace("\\", "/") if p else p


# --------------------------------------------------------------------------- #
#  Toolchain discovery (glob the IDE plugins dir; resilient to version bumps)
# --------------------------------------------------------------------------- #

@dataclass
class Toolchain:
    ide_root: str
    gcc_bin: Optional[str] = None
    make_bin: Optional[str] = None
    cmake_bin: Optional[str] = None
    ninja_bin: Optional[str] = None
    programmer_cli: Optional[str] = None
    openocd_bin: Optional[str] = None
    openocd_scripts: Optional[str] = None


def _find_first(plugins: Path, pattern: str, subpath: str) -> Optional[str]:
    matches = sorted(
        (d for d in plugins.glob(pattern) if d.is_dir()),
        key=lambda d: d.name,
        reverse=True,
    )
    for d in matches:
        cand = d / subpath
        if cand.exists():
            return _norm(str(cand))
    return None


def discover_toolchain(ide_root: Optional[str] = None) -> Toolchain:
    """Locate bundled gcc/make/cmake/ninja/programmer inside a CubeIDE install."""
    cfg = _load_config()
    if not ide_root:
        ide_root = (cfg.get("toolchain", {}) or {}).get("ide_root") \
            or os.environ.get("STM32_IDE_ROOT") \
            or "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE"
    ide_root = _norm(ide_root)
    plugins = Path(ide_root) / "plugins"

    tc = Toolchain(ide_root=ide_root)
    if plugins.is_dir():
        ext = "com.st.stm32cube.ide.mcu.externaltools."
        tc.gcc_bin = _find_first(plugins, ext + "gnu-tools-for-stm32.*win32*", "tools/bin")
        tc.make_bin = _find_first(plugins, ext + "make.win32*", "tools/bin")
        tc.cmake_bin = _find_first(plugins, ext + "cmake.win32*", "tools/bin")
        tc.ninja_bin = _find_first(plugins, ext + "ninja.win32*", "tools/bin")
        tc.programmer_cli = _find_first(
            plugins, ext + "cubeprogrammer.win32*", "tools/bin/STM32_Programmer_CLI.exe"
        )
        tc.openocd_bin = _find_first(plugins, ext + "openocd.win32*", "tools/bin")
        # OpenOCD's ST config scripts live in a SEPARATE plugin (mcu.debug.openocd),
        # not next to openocd.exe.
        tc.openocd_scripts = _find_first(
            plugins, "com.st.stm32cube.ide.mcu.debug.openocd*",
            "resources/openocd/st_scripts",
        )

    # Config values (if present and non-empty) win over discovery.
    tcfg = cfg.get("toolchain", {}) or {}
    for k, v in tcfg.items():
        if v and hasattr(tc, k):
            setattr(tc, k, _norm(v))
    return tc


def _build_env(tc: Toolchain) -> dict:
    """PATH with gcc + make tools (sh/mkdir/rm) prepended, so make recipes work."""
    env = os.environ.copy()
    extra = [p for p in (tc.gcc_bin, tc.make_bin, tc.cmake_bin, tc.ninja_bin) if p]
    if extra:
        env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])
    return env


def _run(cmd, cwd, env, timeout=600) -> dict:
    """Run a subprocess, capture everything, never raise on non-zero."""
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, env=env, timeout=timeout,
            capture_output=True, text=True,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "cmd": cmd if isinstance(cmd, str) else " ".join(cmd),
            "stdout": proc.stdout[-20000:],
            "stderr": proc.stderr[-20000:],
        }
    except subprocess.TimeoutExpired as e:
        return {"ok": False, "returncode": -1, "cmd": str(cmd),
                "stdout": (e.stdout or ""), "stderr": f"TIMEOUT after {timeout}s"}
    except FileNotFoundError as e:
        return {"ok": False, "returncode": -1, "cmd": str(cmd),
                "stdout": "", "stderr": f"Executable not found: {e}"}


# --------------------------------------------------------------------------- #
#  MCP server + tools
# --------------------------------------------------------------------------- #

mcp = FastMCP("stm32-template")


@mcp.tool()
def get_config() -> dict:
    """Return the resolved configuration: stm32.config.json merged with the
    auto-discovered toolchain paths. Use this to sanity-check the environment."""
    cfg = _load_config()
    tc = discover_toolchain()
    return {
        "template_dir": _norm(str(TEMPLATE_DIR)),
        "config_file": _norm(str(CONFIG_PATH)),
        "config": cfg,
        "discovered_toolchain": asdict(tc),
        "toolchain_ok": all([tc.gcc_bin, tc.make_bin, tc.programmer_cli]),
    }


@mcp.tool()
def discover_toolchain_tool(ide_root: str = "") -> dict:
    """Locate the bundled compiler/linker/programmer/build tools inside a
    STM32CubeIDE installation by scanning its plugins directory."""
    return asdict(discover_toolchain(ide_root or None))


@mcp.tool()
def create_project(name: str, dest_parent: str, overwrite: bool = False) -> dict:
    """Create a new firmware project by cloning the STM32TemplateProject scaffold.

    Args:
        name:        new project folder name (e.g. "leg_controller_v3").
        dest_parent: directory that will contain the new project folder.
        overwrite:   if True, replace an existing folder of the same name.

    Returns the new project root path; build/flash tools take that path.
    """
    dest_parent_p = Path(dest_parent).resolve()
    dest = dest_parent_p / name
    if dest.exists():
        if not overwrite:
            return {"ok": False, "error": f"{dest} already exists (pass overwrite=True)."}
        shutil.rmtree(dest)
    dest_parent_p.mkdir(parents=True, exist_ok=True)
    shutil.copytree(TEMPLATE_DIR, dest, ignore=COPY_IGNORE)
    return {
        "ok": True,
        "project_dir": _norm(str(dest)),
        "source_subdir": _norm(str(dest / "project")),
        "hint": "Fill code with write_source(), then build() then flash().",
    }


def _safe_join(project_dir: str, rel_path: str) -> Path:
    """Resolve <project_dir>/project/<rel_path>, refusing path escapes."""
    base = (Path(project_dir).resolve() / "project").resolve()
    target = (base / rel_path).resolve()
    if base not in target.parents and target != base:
        raise ValueError(f"Path escapes project source dir: {rel_path}")
    return target


@mcp.tool()
def write_source(project_dir: str, rel_path: str, content: str) -> dict:
    """Write (create or overwrite) a source file inside <project_dir>/project/.

    Args:
        project_dir: a project root returned by create_project.
        rel_path:    path under project/, e.g. "Core/Src/main.c" or "User/Src/motor.c".
        content:     full file contents.
    """
    try:
        target = _safe_join(project_dir, rel_path)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"ok": True, "path": _norm(str(target)), "bytes": len(content.encode("utf-8"))}


@mcp.tool()
def read_source(project_dir: str, rel_path: str) -> dict:
    """Read a source file from <project_dir>/project/ (for inspection/diffing)."""
    try:
        target = _safe_join(project_dir, rel_path)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    if not target.exists():
        return {"ok": False, "error": f"Not found: {rel_path}"}
    return {"ok": True, "path": _norm(str(target)), "content": target.read_text(encoding="utf-8")}


@mcp.tool()
def list_sources(project_dir: str) -> dict:
    """List all files currently under <project_dir>/project/."""
    base = (Path(project_dir).resolve() / "project")
    if not base.exists():
        return {"ok": False, "error": f"No project/ under {project_dir}"}
    files = [
        _norm(str(p.relative_to(base)))
        for p in sorted(base.rglob("*")) if p.is_file()
    ]
    return {"ok": True, "count": len(files), "files": files}


@mcp.tool()
def build(project_dir: str, system: str = "make", jobs: int = 8, clean_first: bool = False) -> dict:
    """Compile + link + objcopy the project. Produces .elf/.hex/.bin under build/.

    Args:
        project_dir: project root from create_project.
        system:      "make" (default) or "cmake".
        jobs:        parallel jobs for make.
        clean_first: wipe the build dir before building.

    Returns the command result plus discovered artifact paths.
    """
    proj = Path(project_dir).resolve()
    if not (proj / "Makefile").exists():
        return {"ok": False, "error": f"No Makefile in {proj} — is this a project dir?"}
    tc = discover_toolchain()
    env = _build_env(tc)

    if system == "cmake":
        if not tc.cmake_bin:
            return {"ok": False, "error": "cmake not found in IDE install."}
        bdir = proj / "build-cmake"
        if clean_first and bdir.exists():
            shutil.rmtree(bdir)
        cmake = str(Path(tc.cmake_bin) / "cmake.exe")
        ninja = str(Path(tc.ninja_bin) / "ninja.exe") if tc.ninja_bin else "ninja"
        cfg = _run(
            [cmake, "-S", ".", "-B", "build-cmake", "-G", "Ninja",
             f"-DCMAKE_MAKE_PROGRAM={ninja}",
             "-DCMAKE_TOOLCHAIN_FILE=cmake/gcc-arm-none-eabi.cmake",
             f"-DTOOLCHAIN_BIN={tc.gcc_bin}"],
            cwd=str(proj), env=env,
        )
        if not cfg["ok"]:
            return {"ok": False, "stage": "configure", **cfg}
        res = _run([cmake, "--build", "build-cmake"], cwd=str(proj), env=env)
        res["artifacts"] = _list_artifacts(proj / "build-cmake")
        res["stage"] = "build"
        return res

    # default: make
    if not tc.make_bin:
        return {"ok": False, "error": "make not found in IDE install."}
    make = str(Path(tc.make_bin) / "make.exe")
    make_vars = [
        f"TOOLCHAIN_BIN={tc.gcc_bin}",
        f"PROGRAMMER={tc.programmer_cli}",
    ]
    if clean_first:
        _run([make, "clean"] + make_vars, cwd=str(proj), env=env)
    res = _run([make, f"-j{jobs}"] + make_vars, cwd=str(proj), env=env)
    res["artifacts"] = _list_artifacts(proj / "build")
    res["stage"] = "build"
    return res


def _list_artifacts(build_dir: Path) -> dict:
    out = {}
    if build_dir.exists():
        for ext in ("elf", "hex", "bin", "map"):
            hits = list(build_dir.glob(f"*.{ext}"))
            if hits:
                out[ext] = _norm(str(hits[0]))
    return out


@mcp.tool()
def list_artifacts(project_dir: str, system: str = "make") -> dict:
    """Return paths to the build outputs (.elf/.hex/.bin/.map)."""
    proj = Path(project_dir).resolve()
    bdir = proj / ("build-cmake" if system == "cmake" else "build")
    arts = _list_artifacts(bdir)
    return {"ok": bool(arts), "build_dir": _norm(str(bdir)), "artifacts": arts}


@mcp.tool()
def flash(project_dir: str, system: str = "make", binary: str = "bin") -> dict:
    """Upload firmware to the MCU via STM32_Programmer_CLI (ST-LINK / SWD).

    Args:
        project_dir: project root.
        system:      which build dir to flash from ("make" or "cmake").
        binary:      "bin" (uses flash.start_address) or "elf"/"hex" (self-addressed).

    Reads the flash settings from stm32.config.json (port/freq/verify/run_after).
    """
    proj = Path(project_dir).resolve()
    tc = discover_toolchain()
    if not tc.programmer_cli or not Path(tc.programmer_cli).exists():
        return {"ok": False, "error": "STM32_Programmer_CLI not found."}
    bdir = proj / ("build-cmake" if system == "cmake" else "build")
    arts = _list_artifacts(bdir)
    if binary not in arts:
        return {"ok": False, "error": f"No .{binary} in {bdir}. Build first.", "artifacts": arts}

    fcfg = (_load_config().get("flash", {}) or {})
    port = fcfg.get("port", "SWD")
    freq = fcfg.get("frequency_khz", 4000)
    addr = fcfg.get("start_address", "0x08000000")
    cmd = [tc.programmer_cli, "-c", f"port={port}", f"freq={freq}"]
    if binary == "bin":
        cmd += ["-w", arts["bin"], addr]
    else:
        cmd += ["-w", arts[binary]]
    if fcfg.get("verify", True):
        cmd.append("-v")
    if fcfg.get("run_after", True):
        cmd.append("-rst")
    res = _run(cmd, cwd=str(proj), env=_build_env(tc), timeout=300)
    res["stage"] = "flash"
    res["flashed"] = arts.get(binary)
    return res


@mcp.tool()
def build_and_flash(project_dir: str, system: str = "make", jobs: int = 8) -> dict:
    """Convenience: build then (only on success) flash. One call for the agent."""
    b = build(project_dir, system=system, jobs=jobs)
    if not b.get("ok"):
        return {"ok": False, "stage": "build", "build": b}
    f = flash(project_dir, system=system)
    return {"ok": f.get("ok", False), "build": b, "flash": f}


@mcp.tool()
def erase(project_dir: str = "") -> dict:
    """Mass-erase the connected MCU's flash via STM32_Programmer_CLI."""
    tc = discover_toolchain()
    if not tc.programmer_cli:
        return {"ok": False, "error": "STM32_Programmer_CLI not found."}
    fcfg = (_load_config().get("flash", {}) or {})
    cmd = [tc.programmer_cli, "-c", f"port={fcfg.get('port', 'SWD')}",
           f"freq={fcfg.get('frequency_khz', 4000)}", "-e", "all"]
    return _run(cmd, cwd=str(THIS_DIR), env=_build_env(tc), timeout=300)


@mcp.tool()
def reset(project_dir: str = "") -> dict:
    """Hardware-reset the connected MCU via STM32_Programmer_CLI."""
    tc = discover_toolchain()
    if not tc.programmer_cli:
        return {"ok": False, "error": "STM32_Programmer_CLI not found."}
    fcfg = (_load_config().get("flash", {}) or {})
    cmd = [tc.programmer_cli, "-c", f"port={fcfg.get('port', 'SWD')}",
           f"freq={fcfg.get('frequency_khz', 4000)}", "-rst"]
    return _run(cmd, cwd=str(THIS_DIR), env=_build_env(tc), timeout=120)


@mcp.tool()
def clean(project_dir: str, system: str = "make") -> dict:
    """Remove the build output directory for a project."""
    proj = Path(project_dir).resolve()
    bdir = proj / ("build-cmake" if system == "cmake" else "build")
    if bdir.exists():
        shutil.rmtree(bdir)
        return {"ok": True, "removed": _norm(str(bdir))}
    return {"ok": True, "removed": None, "note": "nothing to clean"}


# --------------------------------------------------------------------------- #
#  Serial (VCP/UART) communication  —  pyserial, cross-platform (COM* on Win)
# --------------------------------------------------------------------------- #

try:
    import serial as _pyserial
    import serial.tools.list_ports as _list_ports
    _SERIAL_OK = True
except ImportError:                       # server still runs; serial tools warn
    _pyserial = None
    _list_ports = None
    _SERIAL_OK = False

ST_VID = 0x0483  # STMicroelectronics USB VID — marks ST-LINK VCP ports

_LINE_ENDINGS = {"lf": "\n", "cr": "\r", "crlf": "\r\n", "none": ""}

# Open serial connections, keyed by port name (e.g. "COM7"). The port string
# IS the connection id passed to serial_send / serial_read / serial_disconnect.
_serial_conns: dict = {}

# Polling-read tuning (mirrors typical line-oriented VCP behaviour).
_SER_INTER_BYTE = 0.05    # 50 ms between read polls
_SER_SILENCE = 0.20       # 200 ms of silence after data => reply complete


def _serial_cfg() -> dict:
    return (_load_config().get("serial", {}) or {})


def _no_serial() -> dict:
    return {"ok": False,
            "error": "pyserial not installed. Run: pip install pyserial>=3.5"}


def _read_polling(ser, timeout: float, max_bytes: int = 4096) -> bytes:
    """Read until timeout, or until data arrives then goes silent (_SER_SILENCE)."""
    data = bytearray()
    start = time.monotonic()
    last = None
    while True:
        if time.monotonic() - start >= timeout or len(data) >= max_bytes:
            break
        waiting = ser.in_waiting
        if waiting:
            data.extend(ser.read(min(waiting, max_bytes - len(data))))
            last = time.monotonic()
        elif last is not None and (time.monotonic() - last) >= _SER_SILENCE:
            break
        else:
            time.sleep(_SER_INTER_BYTE)
    return bytes(data)


@mcp.tool()
def serial_list_ports() -> dict:
    """List serial ports; ST-LINK VCP ports (USB VID 0x0483) are flagged.

    Use the returned `device` (e.g. "COM7") as the connection id for
    serial_connect / serial_send / serial_read / serial_disconnect.
    """
    if not _SERIAL_OK:
        return _no_serial()
    ports = []
    for p in sorted(_list_ports.comports(), key=lambda x: x.device):
        ports.append({
            "device": p.device,
            "description": p.description,
            "vid": f"0x{p.vid:04X}" if p.vid is not None else None,
            "pid": f"0x{p.pid:04X}" if p.pid is not None else None,
            "serial_number": p.serial_number,
            "stlink_vcp": (p.vid == ST_VID),
        })
    return {"ok": True, "count": len(ports), "ports": ports}


@mcp.tool()
def serial_connect(port: str, baud: int = 0) -> dict:
    """Open a serial connection to a board's VCP/UART.

    Args:
        port: serial device, e.g. "COM7" (see serial_list_ports).
        baud: baud rate; 0 => use config serial.baud (default 115200).

    The connection persists across tool calls; its id is `port`.
    """
    if not _SERIAL_OK:
        return _no_serial()
    baud = baud or int(_serial_cfg().get("baud", 115200))
    existing = _serial_conns.get(port)
    if existing is not None and existing.is_open:
        return {"ok": True, "port": port, "baud": baud, "note": "already open"}
    try:
        ser = _pyserial.Serial(port=port, baudrate=baud, timeout=0.1, write_timeout=1.0)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
    except Exception as e:                 # serial.SerialException, OSError, ...
        return {"ok": False, "error": f"Could not open {port}: {e}",
                "hint": "Port may be held by another app (CubeIDE monitor, PuTTY, Tera Term)."}
    _serial_conns[port] = ser
    return {"ok": True, "port": port, "baud": baud}


@mcp.tool()
def serial_send(port: str, data: str, read_response: bool = True,
                read_timeout: float = 2.0, line_ending: str = "") -> dict:
    """Send a line to the board and (optionally) read its reply.

    Args:
        port:          connection id from serial_connect.
        data:          text to send.
        read_response: if True, wait for and return the reply.
        read_timeout:  max seconds to wait for the reply.
        line_ending:   "lf"|"cr"|"crlf"|"none"; "" => config serial.line_ending (default lf).
    """
    if not _SERIAL_OK:
        return _no_serial()
    ser = _serial_conns.get(port)
    if ser is None or not ser.is_open:
        return {"ok": False, "error": f"No open connection '{port}'. Call serial_connect first."}
    le = line_ending or str(_serial_cfg().get("line_ending", "lf"))
    payload = (data + _LINE_ENDINGS.get(le, "\n")).encode("utf-8")
    try:
        ser.reset_input_buffer()
        ser.write(payload)
        ser.flush()
    except Exception as e:
        return {"ok": False, "error": f"Write failed: {e}"}
    out = {"ok": True, "port": port, "sent": data}
    if read_response:
        try:
            raw = _read_polling(ser, timeout=read_timeout)
            out["response"] = raw.decode("utf-8", errors="replace").strip()
        except Exception as e:
            out["ok"] = False
            out["error"] = f"Read failed: {e}"
    return out


@mcp.tool()
def serial_read(port: str, timeout: float = 2.0, max_bytes: int = 4096) -> dict:
    """Read whatever the board emits within `timeout` (e.g. boot banner / logs)."""
    if not _SERIAL_OK:
        return _no_serial()
    ser = _serial_conns.get(port)
    if ser is None or not ser.is_open:
        return {"ok": False, "error": f"No open connection '{port}'. Call serial_connect first."}
    raw = _read_polling(ser, timeout=timeout, max_bytes=max_bytes)
    return {"ok": True, "port": port,
            "data": raw.decode("utf-8", errors="replace").strip(),
            "bytes": len(raw)}


@mcp.tool()
def serial_disconnect(port: str) -> dict:
    """Close a serial connection opened by serial_connect."""
    if not _SERIAL_OK:
        return _no_serial()
    ser = _serial_conns.pop(port, None)
    if ser is None:
        return {"ok": True, "note": f"no open connection '{port}'"}
    try:
        if ser.is_open:
            ser.close()
    except Exception:
        pass
    return {"ok": True, "port": port, "closed": True}


# --------------------------------------------------------------------------- #
#  SWD memory read/write  —  one-shot via STM32_Programmer_CLI (mode=HOTPLUG)
# --------------------------------------------------------------------------- #
#  HOTPLUG attaches to a RUNNING target without resetting it, so these read
#  live RAM / peripheral registers. SWD memory access shares the ST-LINK with
#  an open serial VCP (separate USB interface) but NOT with a concurrent flash.

def _swd_conn_args() -> list:
    """STM32_Programmer_CLI connection args for a non-intrusive (running) attach."""
    fcfg = (_load_config().get("flash", {}) or {})
    scfg = (_load_config().get("swd", {}) or {})
    port = fcfg.get("port", "SWD")
    freq = fcfg.get("frequency_khz", 4000)
    mode = scfg.get("connect_mode", "HOTPLUG")
    return ["-c", f"port={port}", f"freq={freq}", f"mode={mode}"]


def _nm_bin() -> Optional[str]:
    tc = discover_toolchain()
    if not tc.gcc_bin:
        return None
    cand = Path(tc.gcc_bin) / "arm-none-eabi-nm.exe"
    return str(cand) if cand.exists() else "arm-none-eabi-nm"


def _resolve_symbol(elf_path: str, name: str) -> Optional[tuple]:
    """Return (address, size_bytes) for a symbol via arm-none-eabi-nm, or None.

    nm -S --defined-only emits:  "<addr> <size> <type> <name>"  (size optional).
    """
    nm = _nm_bin()
    if not nm:
        return None
    res = _run([nm, "-S", "--defined-only", elf_path],
               cwd=str(THIS_DIR), env=os.environ.copy(), timeout=30)
    if not res["ok"]:
        return None
    for line in res["stdout"].splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[3] == name:        # addr size type name
            try:
                return int(parts[0], 16), int(parts[1], 16)
            except ValueError:
                continue
        if len(parts) == 3 and parts[2] == name:         # addr type name (no size)
            try:
                return int(parts[0], 16), 4
            except ValueError:
                continue
    return None


def _find_elf_for(project_dir: str, system: str, elf: str) -> Optional[str]:
    """Resolve an .elf path: explicit `elf` wins, else newest in the build dir."""
    if elf:
        return elf if Path(elf).exists() else None
    if not project_dir:
        return None
    bdir = Path(project_dir).resolve() / ("build-cmake" if system == "cmake" else "build")
    return _list_artifacts(bdir).get("elf")


def _parse_mem_words(stdout: str) -> list:
    """Extract hex words from STM32_Programmer_CLI read output.

    Data rows look like:  0x20000000 : 00000001 00000002 00000003 00000004
    """
    vals = []
    for line in stdout.splitlines():
        m = re.match(r"\s*0x[0-9A-Fa-f]+\s*:\s*(.+)", line)
        if not m:
            continue
        for tok in m.group(1).split():
            t = tok[2:] if tok.lower().startswith("0x") else tok
            if re.fullmatch(r"[0-9A-Fa-f]+", t):
                vals.append("0x" + t.upper())
    return vals


def _resolve_target(address: str, symbol: str, project_dir: str, system: str,
                    elf: str, width: int) -> dict:
    """Shared address/symbol resolution for read_memory / write_memory.

    Returns {"addr": "0x........", "width": int, "symbol": <name or "">} or
    {"error": ...}.
    """
    if symbol:
        elf_path = _find_elf_for(project_dir, system, elf)
        if not elf_path:
            return {"error": "Need an .elf for symbol lookup (pass elf= or project_dir=)."}
        resolved = _resolve_symbol(elf_path, symbol)
        if resolved is None:
            return {"error": f"Symbol '{symbol}' not found in {Path(elf_path).name}."}
        addr_int, size = resolved
        if size in (1, 2):                  # auto-detect width from symbol size
            width = {1: 8, 2: 16}[size]
        return {"addr": f"0x{addr_int:08X}", "width": width, "symbol": symbol}
    if address:
        try:
            addr_int = int(address, 0)
        except ValueError:
            return {"error": f"Invalid address: {address}"}
        return {"addr": f"0x{addr_int:08X}", "width": width, "symbol": ""}
    return {"error": "Provide address or symbol."}


@mcp.tool()
def read_memory(address: str = "", symbol: str = "", project_dir: str = "",
                system: str = "make", elf: str = "", count: int = 1,
                width: int = 32) -> dict:
    """Read live memory from a RUNNING target over SWD (non-intrusive HOTPLUG).

    Specify either:
        address: hex string, e.g. "0x20000000", OR
        symbol:  a variable name — needs the .elf (pass `elf`, or `project_dir`
                 [+ `system`] to locate the latest build's .elf). Access width
                 is auto-detected from the symbol's size.

    Args:
        count: number of `width`-bit units to read.
        width: 8, 16, or 32 bits.

    Returns hex `values`. Reads without resetting the MCU.
    """
    tc = discover_toolchain()
    if not tc.programmer_cli or not Path(tc.programmer_cli).exists():
        return {"ok": False, "error": "STM32_Programmer_CLI not found."}
    if width not in (8, 16, 32):
        return {"ok": False, "error": "width must be 8, 16, or 32."}

    tgt = _resolve_target(address, symbol, project_dir, system, elf, width)
    if "error" in tgt:
        return {"ok": False, "error": tgt["error"]}
    addr, width = tgt["addr"], tgt["width"]

    nbytes = max(count * (width // 8), width // 8)
    cmd = [tc.programmer_cli] + _swd_conn_args() + [f"-r{width}", addr, str(nbytes)]
    res = _run(cmd, cwd=str(THIS_DIR), env=_build_env(tc), timeout=60)
    res["stage"] = "read_memory"
    res["address"] = addr
    res["width"] = width
    if tgt["symbol"]:
        res["symbol"] = tgt["symbol"]
    if res["ok"]:
        res["values"] = _parse_mem_words(res.get("stdout", ""))[:count]
    return res


@mcp.tool()
def write_memory(value: str, address: str = "", symbol: str = "",
                 project_dir: str = "", system: str = "make", elf: str = "",
                 width: int = 32) -> dict:
    """Write a value to live memory on a RUNNING target over SWD (HOTPLUG).

    Provide `value` (hex "0xFF" or decimal "255") plus either `address` or
    `symbol` (symbol needs the .elf — pass elf= or project_dir=). Handy for
    poking peripheral registers or variables without resetting the MCU.

    Args:
        width: 8, 16, or 32 bits (auto-detected from symbol size if a symbol).
    """
    tc = discover_toolchain()
    if not tc.programmer_cli or not Path(tc.programmer_cli).exists():
        return {"ok": False, "error": "STM32_Programmer_CLI not found."}
    if width not in (8, 16, 32):
        return {"ok": False, "error": "width must be 8, 16, or 32."}
    try:
        val_int = int(value, 0)
    except (ValueError, TypeError):
        return {"ok": False, "error": f"Invalid value: {value}"}

    tgt = _resolve_target(address, symbol, project_dir, system, elf, width)
    if "error" in tgt:
        return {"ok": False, "error": tgt["error"]}
    addr, width = tgt["addr"], tgt["width"]

    cmd = [tc.programmer_cli] + _swd_conn_args() + [f"-w{width}", addr, f"0x{val_int:X}"]
    res = _run(cmd, cwd=str(THIS_DIR), env=_build_env(tc), timeout=60)
    res["stage"] = "write_memory"
    res["address"] = addr
    res["width"] = width
    res["wrote"] = f"0x{val_int:X}"
    if tgt["symbol"]:
        res["symbol"] = tgt["symbol"]
    return res


# --------------------------------------------------------------------------- #
#  Live memory monitoring  —  persistent OpenOCD + TCL socket (Phase 2)
# --------------------------------------------------------------------------- #
#  A background thread polls variables over OpenOCD's TCL RPC port without
#  resetting or halting the running target, writing samples to a ring buffer
#  + JSONL file. Uses the bundled OpenOCD with ST's `stlink-dap.cfg` (the `hla`
#  stlink.cfg trips an "infinite eval recursion" bug in ST's swj-dp.tcl).
#
#  NOTE: a live session OWNS the ST-LINK/SWD link. While one is running, `flash`
#  and the CLI-based `read_memory`/`write_memory` will fail — stop it first.

_TCL_TERM = b"\x1a"            # OpenOCD TCL RPC command/response terminator
_LIVE_MIN_INTERVAL_MS = 100
_LIVE_RING = 200              # in-memory samples kept per session


@dataclass
class _LiveVar:
    name: str
    address: int
    width: int = 32            # 8/16/32
    is_float: bool = False


@dataclass
class _LiveSession:
    session_id: str
    variables: list
    interval_ms: int
    output_path: str
    tcl_port: int
    process: object = None
    sock: object = None
    thread: object = None
    stop_event: object = field(default_factory=threading.Event)
    ring: object = field(default_factory=lambda: collections.deque(maxlen=_LIVE_RING))
    start_time: float = 0.0
    read_count: int = 0
    error_count: int = 0


_live_sessions: dict = {}


def _openocd_base_cmd(tc: Toolchain, tcl_port: Optional[int]) -> list:
    """Base OpenOCD argv: scripts dir + ST interface/target + port settings.

    tcl_port=None disables the TCL server (one-shot use); an int enables it.
    GDB/telnet servers are always disabled to avoid port clashes with a debugger.
    """
    scfg = (_load_config().get("swd", {}) or {})
    iface = scfg.get("openocd_interface_cfg", "interface/stlink-dap.cfg")
    target = scfg.get("openocd_target_cfg", "target/stm32f4x.cfg")
    exe = str(Path(tc.openocd_bin) / "openocd.exe")
    cmd = [exe, "-s", tc.openocd_scripts,
           "-c", "gdb_port disabled", "-c", "telnet_port disabled"]
    cmd += ["-c", "tcl_port disabled"] if tcl_port is None else ["-c", f"tcl_port {tcl_port}"]
    cmd += ["-f", iface, "-f", target]
    return cmd


def _tcl_cmd(sock, cmd: str, timeout: float = 3.0) -> str:
    """Send one command over OpenOCD's TCL RPC socket and return the response."""
    sock.sendall(cmd.encode() + _TCL_TERM)
    sock.settimeout(timeout)
    buf = bytearray()
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("OpenOCD TCL connection closed")
        buf.extend(chunk)
        if _TCL_TERM[0] in buf:
            return buf[: buf.index(_TCL_TERM[0])].decode(errors="replace")


def _start_persistent_openocd(tc: Toolchain, tcl_port: int):
    """Launch OpenOCD (init, no shutdown) and connect to its TCL port."""
    cmd = _openocd_base_cmd(tc, tcl_port) + ["-c", "init"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.monotonic() + 6.0
    while time.monotonic() < deadline:
        try:
            return proc, socket.create_connection(("127.0.0.1", tcl_port), timeout=2.0)
        except OSError:
            if proc.poll() is not None:
                _, err = proc.communicate(timeout=2)
                raise RuntimeError(
                    f"OpenOCD exited (code {proc.returncode}): "
                    f"{err.decode(errors='replace')[-600:]}"
                )
            time.sleep(0.2)
    proc.terminate()
    raise RuntimeError(f"Could not reach OpenOCD TCL port {tcl_port} in time.")


def _ocd_read_cmd(width: int) -> str:
    return {8: "mdb", 16: "mdh", 32: "mdw"}.get(width, "mdw")


def _parse_mdw(resp: str) -> Optional[int]:
    """Parse a single value out of `0x20000000: 00000001` style TCL output."""
    m = re.search(r"0x[0-9A-Fa-f]+:\s*([0-9A-Fa-f]+)", resp)
    return int(m.group(1), 16) if m else None


def _resolve_live_vars(variables_json: str, elf_path: Optional[str]) -> list:
    """Parse the `variables` JSON spec into resolved _LiveVar entries.

    Items may be: a symbol-name string; {"symbol": .., "type":"float"?, "width"?};
    or {"address":"0x..", "name"?, "width"?}.
    """
    specs = json.loads(variables_json)
    if not isinstance(specs, list):
        raise ValueError("variables must be a JSON array")
    out = []
    for spec in specs:
        if isinstance(spec, str):
            spec = {"symbol": spec}
        if not isinstance(spec, dict):
            raise ValueError(f"bad variable spec: {spec!r}")
        is_float = str(spec.get("type", "")).lower() == "float"
        if "symbol" in spec:
            if not elf_path:
                raise ValueError(f"elf required to resolve symbol '{spec['symbol']}'")
            res = _resolve_symbol(elf_path, spec["symbol"])
            if res is None:
                raise ValueError(f"symbol '{spec['symbol']}' not found in {Path(elf_path).name}")
            addr, size = res
            width = int(spec.get("width", {1: 8, 2: 16}.get(size, 32)))
            out.append(_LiveVar(spec.get("name", spec["symbol"]), addr, width, is_float))
        elif "address" in spec:
            addr = int(spec["address"], 0)
            out.append(_LiveVar(spec.get("name", f"0x{addr:08X}"),
                                addr, int(spec.get("width", 32)), is_float))
        else:
            raise ValueError(f"variable needs 'symbol' or 'address': {spec!r}")
    return out


def _run_live_session(sess: _LiveSession) -> None:
    """Background daemon: poll each variable each interval, append to ring + JSONL."""
    try:
        out_f = open(sess.output_path, "a", encoding="utf-8")
    except OSError:
        sess.error_count += 1
        return
    try:
        while not sess.stop_event.is_set():
            t0 = time.monotonic()
            values = {}
            try:
                for v in sess.variables:
                    resp = _tcl_cmd(sess.sock, f"{_ocd_read_cmd(v.width)} 0x{v.address:08X} 1")
                    raw = _parse_mdw(resp)
                    if raw is None:
                        values[v.name] = None
                    elif v.is_float and v.width == 32:
                        values[v.name] = round(struct.unpack("<f", struct.pack("<I", raw))[0], 6)
                    else:
                        values[v.name] = raw
            except (OSError, ConnectionError):
                sess.error_count += 1
                break
            entry = {"t": round(time.time(), 3),
                     "elapsed_s": round(time.monotonic() - sess.start_time, 3),
                     "values": values}
            sess.ring.append(entry)
            sess.read_count += 1
            try:
                out_f.write(json.dumps(entry) + "\n")
                out_f.flush()
            except OSError:
                pass
            remaining = sess.interval_ms / 1000.0 - (time.monotonic() - t0)
            if remaining > 0:
                sess.stop_event.wait(remaining)
    finally:
        out_f.close()


@mcp.tool()
def live_memory_start(variables: str, elf: str = "", project_dir: str = "",
                      system: str = "make", interval_ms: int = 500,
                      output_path: str = "") -> dict:
    """Continuously monitor target memory over SWD via a persistent OpenOCD.

    Polls a running target WITHOUT resetting/halting it and streams samples to a
    ring buffer (read with live_memory_read) and a JSONL file.

    Args:
        variables: JSON array. Items can be a symbol name ("blink_count"), or a
            dict {"symbol": "temp", "type": "float"} or
            {"address": "0x20000000", "name": "x", "width": 32}.
        elf / project_dir [+ system]: needed to resolve symbol names (project_dir
            locates the latest build .elf; `elf` overrides).
        interval_ms: poll period (min 100).
        output_path: JSONL path (default: temp dir / live_memory_<id>.jsonl).

    Only one session at a time (it owns the ST-LINK). Stop it before flashing or
    using read_memory/write_memory.
    """
    tc = discover_toolchain()
    if not tc.openocd_bin or not tc.openocd_scripts:
        return {"ok": False, "error": "OpenOCD or its ST scripts not found in the CubeIDE install."}
    for sid, s in list(_live_sessions.items()):
        if s.thread and s.thread.is_alive():
            return {"ok": False, "error": f"A live session is already active ({sid}). Stop it first.",
                    "active_session": sid}

    elf_path = _find_elf_for(project_dir, system, elf)
    try:
        resolved = _resolve_live_vars(variables, elf_path)
    except (json.JSONDecodeError, ValueError) as e:
        return {"ok": False, "error": f"variables: {e}"}
    if not resolved:
        return {"ok": False, "error": "no variables to monitor."}

    interval_ms = max(int(interval_ms), _LIVE_MIN_INTERVAL_MS)
    tcl_port = int((_load_config().get("swd", {}) or {}).get("tcl_port", 6666))
    sid = uuid.uuid4().hex[:8]
    if not output_path:
        output_path = str(Path(tempfile.gettempdir()) / f"live_memory_{sid}.jsonl")

    try:
        proc, sock = _start_persistent_openocd(tc, tcl_port)
    except RuntimeError as e:
        return {"ok": False, "error": str(e)}

    sess = _LiveSession(session_id=sid, variables=resolved, interval_ms=interval_ms,
                        output_path=output_path, tcl_port=tcl_port,
                        process=proc, sock=sock, start_time=time.monotonic())
    sess.thread = threading.Thread(target=_run_live_session, args=(sess,),
                                   daemon=True, name=f"live-mem-{sid}")
    _live_sessions[sid] = sess
    sess.thread.start()
    return {
        "ok": True,
        "session_id": sid,
        "output_path": _norm(output_path),
        "interval_ms": interval_ms,
        "variables": [{"name": v.name, "address": f"0x{v.address:08X}",
                       "width": v.width, "float": v.is_float} for v in resolved],
    }


@mcp.tool()
def live_memory_read(session_id: str, last_n: int = 10) -> dict:
    """Return the most recent samples from a live_memory session's ring buffer."""
    sess = _live_sessions.get(session_id)
    if sess is None:
        return {"ok": False, "error": f"no session '{session_id}'.",
                "active": [k for k, s in _live_sessions.items() if s.thread and s.thread.is_alive()]}
    last_n = max(1, min(int(last_n), _LIVE_RING))
    samples = list(sess.ring)[-last_n:]
    alive = bool(sess.thread and sess.thread.is_alive())
    return {"ok": True, "session_id": session_id, "running": alive,
            "read_count": sess.read_count, "error_count": sess.error_count,
            "samples": samples}


@mcp.tool()
def live_memory_stop(session_id: str) -> dict:
    """Stop a live_memory session: end the thread, kill OpenOCD, free the ST-LINK."""
    sess = _live_sessions.pop(session_id, None)
    if sess is None:
        return {"ok": False, "error": f"no session '{session_id}'."}
    sess.stop_event.set()
    if sess.thread and sess.thread.is_alive():
        sess.thread.join(timeout=5)
    if sess.sock:
        try:
            sess.sock.close()
        except OSError:
            pass
    if sess.process:
        try:
            sess.process.terminate()
            sess.process.wait(timeout=5)
        except Exception:
            try:
                sess.process.kill()
            except Exception:
                pass
    return {"ok": True, "session_id": session_id,
            "duration_s": round(time.monotonic() - sess.start_time, 1),
            "read_count": sess.read_count, "error_count": sess.error_count,
            "output_path": _norm(sess.output_path)}


if __name__ == "__main__":
    mcp.run()  # stdio transport
