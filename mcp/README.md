# STM32 Template MCP Server

An MCP server that lets an agent **scaffold → fill → build → flash** STM32F4
firmware using the toolchain bundled inside STM32CubeIDE — no IDE GUI involved.

## Install

```powershell
cd C:\Development\STM32TemplateProject\mcp
python -m venv .venv ; .\.venv\Scripts\Activate.ps1     # optional
pip install -r requirements.txt
```

Requires Python 3.10+. Verified here on Python 3.12 with `mcp` installed.

## Run / register

The server speaks MCP over **stdio**. Register it with your client/agent. Example
(`claude_desktop_config.example.json`):

```json
{
  "mcpServers": {
    "stm32-template": {
      "command": "python",
      "args": ["C:/Development/STM32TemplateProject/mcp/stm32_mcp_server.py"],
      "env": {
        "STM32_TEMPLATE_DIR": "C:/Development/STM32TemplateProject",
        "STM32_IDE_ROOT": "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE"
      }
    }
  }
}
```

To smoke-test standalone: `python stm32_mcp_server.py` (it will wait for an MCP
client on stdio).

## Tools exposed

| Tool                     | Purpose |
|--------------------------|---------|
| `get_config`             | Resolved config + discovered toolchain paths + `toolchain_ok` flag. |
| `discover_toolchain_tool`| Locate gcc/make/cmake/ninja/programmer in a CubeIDE install. |
| `create_project`         | Clone the template to `<dest_parent>/<name>`. Returns `project_dir`. |
| `write_source`           | Write/overwrite a file under `<project>/project/` (e.g. `Core/Src/main.c`). |
| `read_source`            | Read a file back from `project/`. |
| `list_sources`           | List all files under `project/`. |
| `build`                  | `make` (default) or `cmake` build → `.elf/.hex/.bin`; returns artifacts + size. |
| `list_artifacts`         | Paths to the latest build outputs. |
| `flash`                  | Upload via `STM32_Programmer_CLI` (ST-LINK/SWD). Reads `flash` block of config. |
| `build_and_flash`        | Build then flash in one call (flashes only if build succeeds). |
| `erase` / `reset`        | Mass-erase / hardware-reset the connected MCU. |
| `clean`                  | Remove a project's build dir. |
| `serial_list_ports`      | List serial ports; flags ST-LINK VCP ports (USB VID 0x0483). |
| `serial_connect`         | Open a VCP/UART (e.g. `COM7`); id is the port string. Baud from `serial` config. |
| `serial_send`            | Send a line, optionally read the reply (polling read). |
| `serial_read`            | Read async board output (boot banner / logs) within a timeout. |
| `serial_disconnect`      | Close a serial connection. |
| `read_memory`            | Read live RAM/peripherals of a **running** target over SWD (by address or ELF symbol). |
| `write_memory`           | Write live memory of a **running** target over SWD (by address or ELF symbol). |
| `live_memory_start`      | Stream variables continuously via a persistent OpenOCD (no halt); → `session_id` + JSONL. |
| `live_memory_read`       | Return the most recent samples from a live session's ring buffer. |
| `live_memory_stop`       | Stop the session, kill OpenOCD, release the ST-LINK. |

## Typical agent flow

```
create_project(name="leg_ctrl", dest_parent="C:/robot/fw")
  -> project_dir
write_source(project_dir, "Core/Src/main.c", "<generated firmware>")
write_source(project_dir, "User/Src/motor.c", "...")          # optional modules
build(project_dir, system="make")                              # -> .elf/.hex/.bin
flash(project_dir)                                             # -> programs the MCU
```

Or simply `build_and_flash(project_dir)`.

## Design notes

- **Toolchain auto-discovery**: paths are found by globbing the CubeIDE `plugins/`
  dir, so the server keeps working after IDE updates rename the version-stamped
  folders. Values in `stm32.config.json > toolchain` override discovery.
- **PATH handling**: the gcc and `make` tool dirs are prepended to `PATH` for each
  build (the `make` plugin provides the `sh/mkdir/rm` that the Makefile recipes need).
- **Safety**: `write_source`/`read_source` refuse paths that escape `project/`.
- **Robustness**: every subprocess is captured (stdout/stderr), has a timeout, and
  never raises — tools always return a JSON-able dict with `ok`/`returncode`.
- **Retargeting**: change `mcu`/`firmware_pack` in `stm32.config.json` (and the
  startup/linker files) to target another STM32F4 part; both build systems pick it up.

## Hardware-in-the-loop (serial + live memory)

After flashing, the agent can talk to and observe the running board:

- **Serial/VCP**: `serial_connect("COM7")` → `serial_send(port, "PING")` → `serial_disconnect(port)`.
  Baud / line-ending defaults come from the `serial` block in `stm32.config.json`.
  Needs `pyserial` (in `requirements.txt`); the server still starts without it and the
  serial tools return a clear "not installed" message.
- **Live memory over SWD**: `read_memory`/`write_memory` use `STM32_Programmer_CLI` in
  `mode=HOTPLUG`, which attaches to a **running** target *without* resetting it. Address a
  raw location (`address="0x20000000"`) or a variable by name (`symbol="blink"`,
  resolved from the build's `.elf` via the bundled `arm-none-eabi-nm`). A serial VCP and
  SWD memory access can be used at the same time (separate USB interfaces); a memory op
  and a flash cannot.

`read_memory`/`write_memory` are one-shot (each spawns the CLI, ~0.5–1 s). For
continuous **sub-second polling**, use the `live_memory_*` tools:

- **Live monitoring** runs a *persistent* OpenOCD (the bundled one) connected over its
  TCL RPC port and polls your variables on a background thread — without halting or
  resetting the target. Samples land in a ring buffer (`live_memory_read`) and a JSONL
  file. Example: `live_memory_start('["g_blink_count","g_led_index"]', project_dir=..., interval_ms=250)`.
- It uses ST's **`interface/stlink-dap.cfg`** (the `dapdirect` driver). The older
  `hla` `stlink.cfg` trips an "infinite eval recursion" bug in ST's `swj-dp.tcl` with
  this OpenOCD build — `stm32.config.json > swd.openocd_interface_cfg` is set accordingly.
- A live session **owns the ST-LINK**: stop it (`live_memory_stop`) before `flash`,
  `read_memory`, or `write_memory`. Only one session at a time.

Verified end-to-end on an **STM32F407G-DISC1**: build → flash → live-monitor a `volatile`
counter incrementing on the running board (LED chase on PD12–15), then clean release.

## Limitations / next steps

- Flashing assumes an ST-LINK over SWD via `STM32_Programmer_CLI`. For J-Link, add a
  variant of the `flash` tool.
- Live monitoring supports scalar symbols/addresses (8/16/32-bit, optional float). Struct
  auto-expansion (GDB `ptype /o`) and multi-board probe targeting are possible future adds.
- The default HSI clock in `main.c` is conservative (16 MHz). Production firmware
  should configure the PLL for the target board's crystal.
