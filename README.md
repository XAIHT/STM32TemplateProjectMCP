<div align="center">

# ⚡ STM32 Template Project, MCP!

<em>"scaffold → write → build → flash → verify" — STM32F4 firmware, programmatically, no IDE GUI, agent-drivable.</em>

<br/>

![Template](https://img.shields.io/badge/Template-v0.1.0-1E90FF?style=flat-square)
![Target](https://img.shields.io/badge/Target-STM32F407VG-03234B?style=flat-square&logo=stmicroelectronics&logoColor=white)
![Board](https://img.shields.io/badge/Board-F407G--DISC1-8A2BE2?style=flat-square)
![Core](https://img.shields.io/badge/Core-Cortex--M4F-0091BD?style=flat-square&logo=arm&logoColor=white)
![Platform](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6?style=flat-square&logo=windows&logoColor=white)

![Toolchain](https://img.shields.io/badge/GCC-14.3.1-A42E2B?style=flat-square&logo=gnu&logoColor=white)
![Language](https://img.shields.io/badge/C-GNU11-00599C?style=flat-square&logo=c&logoColor=white)
![HAL](https://img.shields.io/badge/HAL%2FCMSIS-FW__F4%20V1.28.3-2EA44F?style=flat-square)
![Build](https://img.shields.io/badge/Build-Make%20%2B%20CMake%2BNinja-FE7A16?style=flat-square&logo=cmake&logoColor=white)
![Programmer](https://img.shields.io/badge/CubeProg_CLI-v2.22.0-03234B?style=flat-square)

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![MCP](https://img.shields.io/badge/MCP_tools-23-brightgreen?style=flat-square)
![HIL](https://img.shields.io/badge/HIL-Serial%20%2B%20Live%20SWD-E10098?style=flat-square)
![Verified](https://img.shields.io/badge/HW_verified-F407G--DISC1-success?style=flat-square)

</div>

---

A **self-contained scaffold + MCP server** for generating, building, flashing, and
**observing** STM32F4 firmware programmatically — designed to be driven by an
autonomous agent that auto-modifies a robot's firmware at runtime, **without ever
opening the STM32CubeIDE GUI**. It borrows the compiler, programmer, and driver
libraries bundled *inside* STM32CubeIDE, so one IDE install supplies everything.

- **Target MCU:** STM32F407VG (Cortex‑M4F) — retargetable via `stm32.config.json`
- **Reference board:** **STM32F407G‑DISC1** (on‑board ST‑LINK/V2, 4 user LEDs on PD12–15)
- **Toolchain:** GNU Tools for STM32 (GCC 14.3.1, binutils 2.44), bundled in `C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE`
- **HAL/CMSIS:** referenced from the installed pack `STM32Cube_FW_F4_V1.28.3`
- **Build systems:** GNU Make **and** CMake+Ninja (both verified, identical output)
- **Flash/upload:** STM32CubeProgrammer CLI v2.22.0 over ST‑LINK/SWD
- **Observe (HIL):** serial/VCP **and** live memory over SWD (one‑shot + continuous OpenOCD streaming)
- **MCP:** Python server in `mcp/` exposing **23 tools** (create / build / flash / serial / live‑memory)

> 📖 **Brand new to STM32 or this project?** Start with
> **[`InstructionsGuideForDummies.md`](InstructionsGuideForDummies.md)** — a complete,
> zero‑assumptions walkthrough from *installing everything* → loading code → building →
> flashing → verifying on a real STM32F407G‑DISC1.

---

## ✨ What it does

| Stage | Capability |
|-------|------------|
| **Scaffold** | Clone a complete, buildable project (default firmware = an LED‑chase blinky) to any location. |
| **Author** | Drop generated `.c/.h` into `Core/Src` and `User/Src` — the build auto‑globs them, no Makefile surgery. |
| **Build** | Bundled `arm-none-eabi-gcc` → `.elf` + `.hex` + `.bin` + `.map`, via **Make** or **CMake+Ninja**. |
| **Flash** | Upload to the MCU via `STM32_Programmer_CLI` over ST‑LINK/SWD, with verify + reset. |
| **Observe** | Read/stream live RAM, peripherals, or named ELF symbols over SWD **without halting** the target; talk to the board's serial VCP. |
| **Retarget** | Switch to another STM32F4 part by editing `stm32.config.json` + startup/linker files. |

The HAL/CMSIS driver sources are **referenced** from the firmware pack (not copied),
so each project copy is only a few KB. The **full HAL is compiled into every build**,
so any peripheral the agent uses already links — no per‑project Makefile changes.

---

## 🧱 Layout

```
STM32TemplateProject/
├─ README.md                       # this file
├─ InstructionsGuideForDummies.md  # step-by-step beginner manual (install → flash → verify)
├─ stm32.config.json               # SINGLE SOURCE OF TRUTH (MCU, tool paths, flash/serial/swd opts)
├─ config.mk                       # Make-side defaults (mirror of the JSON)
├─ Makefile                        # GNU Make build  (make / make flash / make clean / …)
├─ CMakeLists.txt                  # CMake build
├─ cmake/
│  └─ gcc-arm-none-eabi.cmake      # CMake toolchain file (arm-none-eabi)
├─ tools/
│  ├─ discover_toolchain.ps1       # find bundled tool paths (robust to IDE updates)
│  └─ vendor_hal.ps1               # optionally copy HAL/CMSIS in for self-containment
├─ mcp/
│  ├─ stm32_mcp_server.py          # the MCP server — 23 tools  <-- integrate with your agent
│  ├─ smoke_test.py                # local create→build smoke test
│  ├─ requirements.txt / pyproject.toml
│  ├─ claude_desktop_config.example.json
│  └─ README.md                    # full MCP tool reference
├─ build/                          # build outputs (.elf/.hex/.bin/.map)  [git-ignored]
└─ project/                        # the STM32 firmware source tree (agent fills this)
   ├─ Core/{Inc,Src,Startup}/      # main.c, IT, MSP, system, startup
   ├─ User/{Inc,Src}/              # application modules go here
   ├─ Drivers/                     # empty (HAL/CMSIS referenced from the pack)
   └─ STM32F407VGTX_FLASH.ld       # linker script (1 MB FLASH @0x08000000, 128 KB RAM)
```

---

## ⚙️ How it works

```
  create_project        write_source            build                  flash / observe
  ──────────────        ────────────            ─────                  ───────────────
  clone template   →    Core/Src/main.c    →    arm-none-eabi-gcc  →   STM32_Programmer_CLI
  to <dest>/<name>      User/Src/*.c            (make | cmake)         over ST-LINK/SWD
                                                ↓                      ↓
                                            .elf .hex .bin .map     LEDs chase · SWD reads
                                                                    serial VCP · live memory
```

1. The **template** is a complete, buildable project (default = an LED‑chase blinky)
   plus the build glue (Make/CMake) and the MCP server.
2. The **MCP** `create_project` **copies** the whole template to a new location.
3. The agent calls `write_source` to drop generated `.c/.h` files into `project/`.
4. `build` runs the bundled GCC → produces `.elf` + `.hex` + `.bin`.
5. `flash` uploads the binary to the MCU; `serial_*` / `read_memory` / `live_memory_*`
   then **prove it's running** on real silicon.

Tool paths are **auto‑discovered** by globbing the STM32CubeIDE `plugins/` directory,
so the server keeps working after IDE updates rename the version‑stamped folders.
Values in `stm32.config.json > toolchain` override discovery.

---

## 🚀 Quick start — command line (no MCP)

Open a terminal in this folder. Tool dirs are baked into `config.mk`; override if your
IDE path differs (see `tools/discover_toolchain.ps1`, which prints the exact paths).

```powershell
# build (GNU Make)
& "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.make.win32_2.2.100.202601091506\tools\bin\make.exe"
# -> build\stm32app.elf / .hex / .bin / .map  (+ prints size)

# build (CMake + Ninja)
$cmake = "C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE\plugins\com.st.stm32cube.ide.mcu.externaltools.cmake.win32_1.1.101.202603101401\tools\bin\cmake.exe"
& $cmake -S . -B build-cmake -G Ninja -DCMAKE_TOOLCHAIN_FILE=cmake/gcc-arm-none-eabi.cmake
& $cmake --build build-cmake

# flash (with an ST-LINK + board attached)
& "...\make.exe" flash
```

**Make targets:** `make` · `make flash` · `make erase` · `make reset` · `make size` ·
`make clean` · `make print-CONFIG`.

> Tip: put the gcc `tools\bin` **and** the `make` plugin's `tools\bin` on `PATH`
> (the latter supplies the `sh/mkdir/rm` the recipes need) and you can just type
> `make`, `make flash`, etc. Full PATH setup is in the
> [Instruction Guide](InstructionsGuideForDummies.md#part-d--make-the-tools-easy-to-call-path).

---

## 🤖 Quick start — via the MCP / agent

Install + register the server (details in [`mcp/README.md`](mcp/README.md)):

```powershell
cd C:\Development\STM32TemplateProject\mcp
python -m venv .venv ; .\.venv\Scripts\Activate.ps1     # optional
pip install -r requirements.txt                          # mcp + pyserial
```

Register it with your MCP client (e.g. Claude Desktop ‑ merge
`mcp/claude_desktop_config.example.json` into `%APPDATA%\Claude\claude_desktop_config.json`),
then a typical agent flow is:

```
create_project(name="leg_ctrl", dest_parent="C:/robot/fw")  ->  project_dir
write_source(project_dir, "Core/Src/main.c", "<generated firmware>")
write_source(project_dir, "User/Src/motor.c", "...")        # optional modules
build_and_flash(project_dir)                                # -> programs the MCU
live_memory_start('["g_blink_count","g_led_index"]', project_dir=project_dir, interval_ms=250)
#   ... watch the counters move on the running board ...
live_memory_stop(session_id)
```

---

## 🧰 MCP tool reference (23 tools)

All tools return a JSON‑able dict with `ok`/`returncode`; none raise. `write_source`
/`read_source` refuse paths that escape `project/`.

**Environment**
| Tool | Purpose |
|------|---------|
| `get_config` | Resolved config + discovered toolchain paths + `toolchain_ok` flag. |
| `discover_toolchain_tool(ide_root="")` | Locate gcc/make/cmake/ninja/programmer in a CubeIDE install. |

**Project lifecycle**
| Tool | Purpose |
|------|---------|
| `create_project(name, dest_parent, overwrite=False)` | Clone the template to `<dest_parent>/<name>`. Returns `project_dir`. |
| `write_source(project_dir, rel_path, content)` | Write/overwrite a file under `project/` (e.g. `Core/Src/main.c`). |
| `read_source(project_dir, rel_path)` | Read a file back. |
| `list_sources(project_dir)` | List everything under `project/`. |
| `clean(project_dir, system="make")` | Remove the build output dir. |

**Build & flash**
| Tool | Purpose |
|------|---------|
| `build(project_dir, system="make", jobs=8, clean_first=False)` | Compile+link+objcopy → `.elf/.hex/.bin`; returns artifacts + size. |
| `list_artifacts(project_dir, system="make")` | Paths to the latest build outputs. |
| `flash(project_dir, system="make", binary="bin")` | Upload via `STM32_Programmer_CLI` (ST‑LINK/SWD). |
| `build_and_flash(project_dir, system="make", jobs=8)` | Build then flash in one call (flashes only on build success). |
| `erase(project_dir="")` / `reset(project_dir="")` | Mass‑erase / hardware‑reset the MCU. |

**Serial / VCP (HIL)**
| Tool | Purpose |
|------|---------|
| `serial_list_ports()` | List COM ports; flags ST‑LINK VCP ports (USB VID `0x0483`). |
| `serial_connect(port, baud=0)` | Open a VCP/UART (e.g. `COM7`). Baud from `serial` config if `0`. |
| `serial_send(port, data, read_response=True, …)` | Send a line, optionally read the reply. |
| `serial_read(port, timeout=2.0, …)` | Read async board output (boot banner / logs). |
| `serial_disconnect(port)` | Close the connection. |

**Live memory over SWD (HIL)**
| Tool | Purpose |
|------|---------|
| `read_memory(address\|symbol, project_dir, …, count, width)` | Read live RAM/peripherals of a **running** target (HOTPLUG, no reset). |
| `write_memory(value, address\|symbol, …)` | Write live memory of a running target. |
| `live_memory_start(variables, project_dir, interval_ms=500, …)` | Stream variables continuously via a persistent OpenOCD → `session_id` + JSONL. |
| `live_memory_read(session_id, last_n=10)` | Most recent samples from the ring buffer. |
| `live_memory_stop(session_id)` | Stop the session, kill OpenOCD, release the ST‑LINK. |

---

## 🔬 Hardware-in-the-loop (serial + live memory)

After flashing, the agent can **talk to** and **observe** the running board:

- **Serial / VCP** — `serial_connect("COM7")` → `serial_send(port, "PING")` →
  `serial_disconnect(port)`. Baud / line‑ending defaults come from the `serial` block
  in `stm32.config.json`. Needs `pyserial`; the server still starts without it and the
  serial tools return a clear "not installed" message.

- **Live memory over SWD** — `read_memory`/`write_memory` use `STM32_Programmer_CLI` in
  `mode=HOTPLUG`, which attaches to a **running** target *without* resetting it. Address
  a raw location (`address="0x20000000"`) or a variable by name (`symbol="g_blink_count"`,
  resolved from the build's `.elf` via the bundled `arm-none-eabi-nm`). These are
  one‑shot (~0.5–1 s each).

- **Continuous streaming** — for sub‑second polling, `live_memory_*` runs a *persistent*
  OpenOCD connected over its TCL RPC port and polls your variables on a background thread
  — without halting or resetting the target. Samples land in a ring buffer
  (`live_memory_read`) and a JSONL file.

> ⚠️ **Two rules for live monitoring:**
> 1. A live session **owns the ST‑LINK** — `live_memory_stop` it before `flash`,
>    `read_memory`, or `write_memory` (only one consumer of the probe at a time). A
>    serial VCP and SWD memory access *can* run together (separate USB interfaces).
> 2. It uses ST's **`interface/stlink-dap.cfg`** (the `dapdirect` driver). The older
>    `hla` `stlink.cfg` trips an *"infinite eval recursion"* bug in ST's `swj-dp.tcl`
>    with this OpenOCD build — `stm32.config.json > swd.openocd_interface_cfg` is set
>    accordingly. Leave it.

---

## 🎯 The reference board: STM32F407G‑DISC1

- Plug into the **mini‑USB (ST‑LINK)** port — it powers *and* programs the board.
- Four user LEDs on **GPIOD**: PD12 green · PD13 orange · PD14 red · PD15 blue
  (defined in `project/Core/Inc/main.h`).
- The default `main.c` runs on the internal **HSI 16 MHz (no PLL)** so it's correct on
  *any* F407 board regardless of crystal, and "chases" the four LEDs while incrementing
  two `volatile` counters (`g_blink_count`, `g_led_index`) that the live‑memory tools
  watch over SWD. **Production firmware should configure the PLL** for full 168 MHz.

---

## 🔁 Retargeting another STM32F4 part

Edit `stm32.config.json` (`mcu` + `firmware_pack`), swap the startup file in
`project/Core/Startup/` and the `.ld` linker script, and adjust `-mcpu/-mfpu` in
`config.mk` / the CMake cache if the core differs. Both build systems read those values.
For families other than F4 you'd also point `firmware_pack` at the matching
`STM32Cube_FW` pack and update the CMSIS include paths. (Full steps in the
[Instruction Guide, PART J](InstructionsGuideForDummies.md#part-j--retargeting-a-different-chip).)

---

## ✅ Verified on this machine

- **`make` build:** 95 objects → `stm32app.elf` (text 4328 / data 20 / bss 1572), `.hex`, `.bin`, exit 0
- **`cmake`+`ninja` build:** identical firmware size, exit 0
- **MCP `create_project` → `build`:** exit 0, all artifacts produced
- **MCP `flash`:** correctly invokes CubeProgrammer v2.22.0 (errors cleanly when no probe attached)
- **End‑to‑end HIL on an STM32F407G‑DISC1:** build → flash → live‑monitor `g_blink_count`
  incrementing while the LED chase runs on PD12–15 → clean probe release

---

## 📂 Key files at a glance

| You want to… | Edit / read |
|--------------|-------------|
| Change the program | `project/Core/Src/main.c` |
| Add a code module | `project/User/Src/*.c` + `project/User/Inc/*.h` |
| Turn on a peripheral | `project/Core/Inc/stm32f4xx_hal_conf.h` |
| Change MCU / tool paths / flash opts | `stm32.config.json` (MCP) + `config.mk` (Make) |
| Discover tool paths on a new machine | `tools/discover_toolchain.ps1` |
| Make a project self-contained (vendor HAL) | `tools/vendor_hal.ps1` |
| Full beginner walkthrough | [`InstructionsGuideForDummies.md`](InstructionsGuideForDummies.md) |
| MCP tool deep-dive | [`mcp/README.md`](mcp/README.md) |

---

## 🛠️ Troubleshooting (quick hits)

| Symptom | Fix |
|---------|-----|
| `arm-none-eabi-gcc: No such file` | Wrong `TOOLCHAIN_BIN` in `config.mk` — re‑run `tools/discover_toolchain.ps1`. |
| `fatal error: stm32f4xx_hal.h: No such file` | Wrong/absent `FW_PACK` — install the FW_F4 pack (see the Guide, PART A2). |
| `undefined reference to HAL_xxx_...` | Enable that module's `#define HAL_xxx_MODULE_ENABLED` in `stm32f4xx_hal_conf.h`. |
| Recipe fails on `mkdir`/`rm`/`sh` | Add the **make** plugin's `tools\bin` to PATH (it ships those helpers). |
| `flash` → "No STLink detected" | Use the **mini‑USB** port; check the driver in Device Manager; `STM32_Programmer_CLI -l`. |
| Live tools → "probe busy" | `live_memory_stop` first — only one ST‑LINK consumer at a time. |

A fuller troubleshooting table lives in
[`InstructionsGuideForDummies.md#troubleshooting`](InstructionsGuideForDummies.md#troubleshooting).

---

<div align="center">
<sub>STM32TemplateProject · target <b>STM32F407VG</b> on <b>STM32F407G‑DISC1</b> ·
GNU Tools for STM32 (GCC 14.3.1) + STM32CubeProgrammer CLI, bundled in STM32CubeIDE ·
Make &amp; CMake+Ninja builds, Serial + Live‑SWD HIL, 23 MCP tools.</sub>
</div>
