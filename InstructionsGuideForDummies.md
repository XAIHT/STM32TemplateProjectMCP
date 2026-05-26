# STM32TemplateProject — Instruction Guide for Dummies

**A complete, hold-your-hand walkthrough: from a blank Windows PC to a blinking,
verified STM32F407G‑DISC1 board.**

This guide assumes **zero prior knowledge**. If you can copy and paste a command
into a terminal, you can do every step here. Wherever a command is shown, copy
the *whole* block.

> **What is this project?**
> `STM32TemplateProject` is a ready-to-build STM32F4 firmware "skeleton" plus the
> glue (Make / CMake) and a Python **MCP server** that let you (or an AI agent)
> **create → write code → build → flash → verify** firmware **without ever opening
> the STM32CubeIDE graphical editor**. It borrows the compiler, programmer, and
> driver libraries that come *bundled inside* STM32CubeIDE, so installing the IDE
> once gives you everything you need.

> **What hardware are we targeting?**
> The **STM32F407G‑DISC1** Discovery board (chip: **STM32F407VG**, an ARM
> Cortex‑M4F). It has a built‑in **ST‑LINK/V2** debugger/programmer — meaning the
> single USB cable both powers the board *and* programs it. No extra programmer
> needed. The four user LEDs are on pins **PD12 (green), PD13 (orange), PD14 (red),
> PD15 (blue)**.

---

## Table of contents

1. [The 10‑second mental model](#1-the-10second-mental-model)
2. [What you need (hardware + a checklist)](#2-what-you-need)
3. [PART A — Install EVERYTHING](#part-a--install-everything)
   - [A1. Install STM32CubeIDE (gives you the compiler, make, cmake, ninja, the programmer, ST‑LINK drivers)](#a1-install-stm32cubeide)
   - [A2. Get the STM32Cube FW_F4 firmware pack (HAL + CMSIS)](#a2-get-the-stm32cube-fw_f4-firmware-pack)
   - [A3. Install Python (only needed for the MCP / agent path)](#a3-install-python-optional)
   - [A4. Confirm the ST‑LINK USB driver](#a4-confirm-the-stlink-usb-driver)
4. [PART B — Put the template on your PC](#part-b--put-the-template-on-your-pc)
5. [PART C — Point the template at your machine (configure paths)](#part-c--point-the-template-at-your-machine)
6. [PART D — Make the tools easy to call (PATH)](#part-d--make-the-tools-easy-to-call-path)
7. [PART E — Put YOUR firmware into the project](#part-e--put-your-firmware-into-the-project)
   - [E1. The simplest edit: change `main.c`](#e1-the-simplest-edit-change-mainc)
   - [E2. Loading code FROM an existing STM32CubeIDE workspace/project](#e2-loading-code-from-an-existing-stm32cubeide-project)
   - [E3. Turning peripherals on (UART, timers, I²C…)](#e3-turning-peripherals-on)
8. [PART F — Build the firmware](#part-f--build-the-firmware)
9. [PART G — Connect & flash the STM32F407G‑DISC1](#part-g--connect--flash-the-board)
10. [PART H — Verify it actually works](#part-h--verify-it-actually-works)
11. [PART I — The MCP / AI‑agent path (optional, advanced)](#part-i--the-mcp--agent-path-optional)
12. [PART J — Retargeting a different STM32 chip](#part-j--retargeting-a-different-chip)
13. [Troubleshooting](#troubleshooting)
14. [One‑page cheat sheet](#onepage-cheat-sheet)
15. [Glossary](#glossary)

---

## 1. The 10‑second mental model

```
  YOUR CODE                BUILD                       UPLOAD                  VERIFY
  ─────────                ─────                       ──────                  ──────
  project/Core/Src/main.c  →  arm-none-eabi-gcc   →   STM32_Programmer_CLI  →  LEDs blink
  project/User/Src/*.c        (make  OR  cmake)       over ST-LINK / SWD       SWD memory reads
                              ↓                        ↓                        serial messages
                          build/stm32app.elf       writes .bin to chip
                                    .hex            flash @ 0x08000000
                                    .bin
```

Everything below is just **doing those four boxes**, slowly and carefully.

---

## 2. What you need

**Hardware**
- [ ] One **STM32F407G‑DISC1** board.
- [ ] One **USB‑A → Mini‑USB** cable (plugs into the **ST‑LINK** mini‑USB port near
      the top edge of the board, *not* the micro‑USB "USB OTG" port at the bottom).
- [ ] A Windows 10/11 PC with a free USB port.

**Software (installed in PART A — don't go get these yet, just so you know the list)**
- [ ] **STM32CubeIDE** — this single installer bundles *all* of:
  the ARM GCC compiler, GNU Make, CMake, Ninja, the STM32CubeProgrammer CLI,
  OpenOCD, and the **ST‑LINK USB driver**.
- [ ] **STM32Cube FW_F4 firmware pack** (`STM32Cube_FW_F4_V1.28.3`) — the HAL +
  CMSIS driver libraries. Easiest to grab through CubeIDE/CubeMX.
- [ ] **Python 3.10+** — *only* if you want the MCP / AI‑agent automation. The plain
  build‑and‑flash path does **not** need Python.

> 💡 On the machine this template was built on, everything already lives at the
> paths shown throughout this guide (e.g. `C:\ST\STM32CubeIDE_2.1.1\...`). If your
> install paths differ, PART C shows you how to discover and update them.

---

# PART A — Install EVERYTHING

## A1. Install STM32CubeIDE

STM32CubeIDE is ST's free, all‑in‑one development environment. **We won't use its
graphical editor much** — we install it because it carries every command‑line tool
this template needs, neatly bundled.

1. Go to **st.com → search "STM32CubeIDE"** (direct: `https://www.st.com/en/development-tools/stm32cubeide.html`).
2. Click **Get Software**, pick the **Windows** installer, accept the licence, and
   download. You'll need a free ST account (or use the email‑link download).
3. Run the downloaded `.exe`. Click **Next** through the wizard and **accept the
   defaults**. When it offers to install the **ST‑LINK / SEGGER drivers**, say
   **yes** — this is what lets Windows talk to your board.
4. Default install location looks like `C:\ST\STM32CubeIDE_<version>\STM32CubeIDE`.
   This template was set up against:

   ```
   C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE
   ```

   Yours may be a different version number — that's fine, PART C handles it.

5. Launch STM32CubeIDE once so it finishes first‑run setup. When it asks for a
   **workspace** folder, accept the default and click **Launch**. You can close it
   afterwards; we mainly needed it installed.

**What you just got (all inside the install folder, under `…\plugins\`):**

| Tool | What it does | Folder name pattern |
|------|--------------|---------------------|
| `arm-none-eabi-gcc` (GCC 14.3.1) | Compiles your C code for the chip | `…externaltools.gnu-tools-for-stm32.*` |
| `make.exe` | Runs the GNU Make build | `…externaltools.make.win32.*` |
| `cmake.exe` | Runs the CMake build | `…externaltools.cmake.win32.*` |
| `ninja.exe` | Fast build engine CMake uses | `…externaltools.ninja.win32.*` |
| `STM32_Programmer_CLI.exe` | Uploads firmware to the board | `…externaltools.cubeprogrammer.win32.*` |
| `openocd.exe` | Live memory monitoring over SWD | `…externaltools.openocd.win32.*` |

> The folder names end in long version numbers that **change with every IDE update**.
> Don't memorize them — PART C has a script that finds them automatically.

## A2. Get the STM32Cube FW_F4 firmware pack

The "firmware pack" is ST's library of driver code (called **HAL** = Hardware
Abstraction Layer, plus **CMSIS** = the ARM core support files). Your firmware
`#include`s these and the build compiles them in. This template expects:

```
C:\Users\<you>\STM32Cube\Repository\STM32Cube_FW_F4_V1.28.3
```

On this machine that is:

```
C:\Users\angel\STM32Cube\Repository\STM32Cube_FW_F4_V1.28.3
```

**Easiest way to get it (through the IDE you just installed):**

1. Open STM32CubeIDE → menu **Help → Manage Embedded Software Packages** (this opens
   the CubeMX package manager).
2. Click the **STM32Cube MCU Packages** tab → expand **STM32F4**.
3. Tick **1.28.3** (or the newest 1.x.y available) → **Install Now**.
4. It downloads into `C:\Users\<you>\STM32Cube\Repository\STM32Cube_FW_F4_<ver>`.

> If you install a **different version** (say `V1.28.4`), that's fine — just note the
> exact folder name; PART C is where you tell the template about it.

**Sanity check** — confirm the pack landed and has the HAL drivers in it:

```powershell
Test-Path "C:\Users\$env:USERNAME\STM32Cube\Repository\STM32Cube_FW_F4_V1.28.3\Drivers\STM32F4xx_HAL_Driver\Src\stm32f4xx_hal.c"
```

It should print `True`.

## A3. Install Python (optional)

**Skip this** if you only want to build and flash from the command line. Install
Python **only** if you plan to use the MCP server (the AI‑agent automation in
PART I).

1. Get Python 3.10 or newer from `https://www.python.org/downloads/windows/`
   (3.12 is verified working here).
2. **On the first installer screen, tick "Add python.exe to PATH"**, then click
   **Install Now**.
3. Verify in a *new* PowerShell window:

   ```powershell
   python --version
   ```

   You want `Python 3.10` or higher.

## A4. Confirm the ST‑LINK USB driver

The ST‑LINK driver was installed in step A1. To confirm it's working, you can wait
until PART G when you actually plug in the board, or verify now:

1. Plug the board into your PC using the **mini‑USB (ST‑LINK)** port.
2. Open **Device Manager** (press `Win+X` → Device Manager).
3. Look under **Universal Serial Bus devices** for **"STM32 STLink"** (no yellow
   warning triangle). If you see it cleanly, the driver is good.

> If it shows up with a ⚠️ warning, reinstall drivers from
> `C:\ST\STM32CubeIDE_*\STM32CubeIDE\...\st-stlink-driver\` (run the bundled
> `dpinst` installer), or install **STM32CubeProgrammer** standalone, which also
> ships the driver.

---

# PART B — Put the template on your PC

This template project lives at:

```
C:\Development\STM32TemplateProject
```

If you already have it there (you do — that's where you're reading this from),
**skip to PART C**.

If you're setting it up on a fresh machine, copy the entire `STM32TemplateProject`
folder there (USB drive, zip, or `git clone` if it's in a repo). The folder you
need contains these top‑level items:

```
STM32TemplateProject\
├─ stm32.config.json     ← SINGLE SOURCE OF TRUTH (chip + all tool paths)
├─ config.mk             ← Make's copy of those settings
├─ Makefile              ← `make`, `make flash`, `make clean`, …
├─ CMakeLists.txt        ← the CMake build
├─ cmake\                ← CMake toolchain file
├─ tools\                ← helper PowerShell scripts
├─ mcp\                  ← the Python MCP server (agent automation)
├─ project\              ← YOUR FIRMWARE SOURCE goes here
└─ build\                ← build outputs appear here (.elf/.hex/.bin)
```

---

# PART C — Point the template at your machine

The template ships with paths that are correct **for the machine it was built on**.
If your STM32CubeIDE version or pack version differs, do this part. If you're on the
original machine and everything in PART A installed to the default places, you can
**skim this and jump to PART D**.

### C1. Auto‑discover your tool paths

There's a script that finds the version‑stamped tool folders for you. Open
PowerShell in the project folder and run:

```powershell
cd C:\Development\STM32TemplateProject
pwsh -File tools\discover_toolchain.ps1 -IdeRoot 'C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE'
```

(Replace the `-IdeRoot` path if your IDE installed elsewhere — point it at the
folder that contains `stm32cubeide.exe`.)

It prints a JSON block like this:

```json
{
  "ide_root":       "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE",
  "gcc_bin":        "C:/ST/.../gnu-tools-for-stm32.14.3.rel1.../tools/bin",
  "make_bin":       "C:/ST/.../make.win32.../tools/bin",
  "cmake_bin":      "C:/ST/.../cmake.win32.../tools/bin",
  "ninja_bin":      "C:/ST/.../ninja.win32.../tools/bin",
  "programmer_cli": "C:/ST/.../cubeprogrammer.win32.../tools/bin/STM32_Programmer_CLI.exe",
  "openocd_bin":    "C:/ST/.../openocd.win32.../tools/bin"
}
```

**Copy those values.** You'll paste them into two files next.

### C2. Update `stm32.config.json` (the master config)

Open `C:\Development\STM32TemplateProject\stm32.config.json` in any text editor
(Notepad is fine). Update these two blocks if your paths differ from the discovery
output above:

- The **`toolchain`** block → paste each discovered path into the matching key
  (`gcc_bin`, `make_bin`, `cmake_bin`, `ninja_bin`, `programmer_cli`).
- The **`firmware_pack` → `path`** → set to your pack folder, e.g.
  `"C:/Users/angel/STM32Cube/Repository/STM32Cube_FW_F4_V1.28.3"`.

> Use **forward slashes** `/` in JSON paths (backslashes need to be doubled and are
> error‑prone). Forward slashes work fine on Windows here.

> **Tip:** You can also leave the `toolchain` paths **empty** (`""`). The MCP server
> will then auto‑discover them at runtime by scanning the IDE's `plugins\` folder —
> handy because it keeps working after IDE updates rename those folders.

### C3. Update `config.mk` (Make's copy)

`stm32.config.json` is read by the MCP/agent. The plain `make` build reads
**`config.mk`** instead (same values, separate file, so Make works standalone).
Open `C:\Development\STM32TemplateProject\config.mk` and confirm/update:

```makefile
TOOLCHAIN_BIN ?= C:/ST/.../gnu-tools-for-stm32.../tools/bin   # = gcc_bin from C1
PROGRAMMER    ?= C:/ST/.../cubeprogrammer.../tools/bin/STM32_Programmer_CLI.exe
FW_PACK       ?= C:/Users/angel/STM32Cube/Repository/STM32Cube_FW_F4_V1.28.3
```

The CMake build has the same defaults baked into `CMakeLists.txt` and
`cmake\gcc-arm-none-eabi.cmake` (the `TOOLCHAIN_BIN` and `FW_PACK` cache variables) —
update those too if you use CMake and your paths changed.

### C4. Verify the config resolves

```powershell
cd C:\Development\STM32TemplateProject
& "C:/ST/.../make.win32.../tools/bin/make.exe" print-CONFIG
```

(Use your real `make.exe` path from C1.) You should see your project name, MCU
flags, the compiler path, the firmware‑pack path, and a HAL source count (~95
files). If `FW_PACK` or `CC` looks wrong, fix `config.mk` and re‑run.

---

# PART D — Make the tools easy to call (PATH)

Typing the full `C:\ST\...\make.exe` path every time is painful. Add the two tool
folders to your `PATH` so you can just type `make`.

**Why two folders?** The compiler lives in the **gcc** `tools\bin`, and the GNU
**make** plugin's `tools\bin` provides not only `make.exe` but also the small Unix
helpers (`sh`, `rm`, `mkdir`) that the Makefile recipes call.

### Option 1 — temporary (just this terminal session)

```powershell
$gcc  = "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/tools/bin"
$make = "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.make.win32_2.2.100.202601091506/tools/bin"
$env:PATH = "$gcc;$make;$env:PATH"
```

(Swap in your real folder names from PART C1.) Now `arm-none-eabi-gcc --version`
and `make --version` should both work **in this window**. When you close the
window, the change is gone.

### Option 2 — permanent (recommended)

1. Press `Win` → type **"environment variables"** → open **"Edit the system
   environment variables"** → **Environment Variables…** button.
2. Under **User variables**, select **Path** → **Edit** → **New**, and add the two
   folders (the gcc `tools\bin` and the make `tools\bin`).
3. **OK** out of all dialogs. **Open a brand‑new PowerShell window** (PATH changes
   only apply to new windows) and confirm:

   ```powershell
   arm-none-eabi-gcc --version
   make --version
   ```

From here on this guide assumes you can type `make` directly. If you skipped this,
just substitute the full `…\make.exe` path wherever you see `make`.

---

# PART E — Put YOUR firmware into the project

All of **your** code goes under the `project\` folder:

```
project\
├─ Core\
│  ├─ Inc\
│  │  ├─ main.h                  ← entry-point header (LED pin #defines live here)
│  │  ├─ stm32f4xx_hal_conf.h    ← which HAL modules are turned ON
│  │  └─ stm32f4xx_it.h
│  ├─ Src\
│  │  ├─ main.c                  ← ★ YOUR main program (default = blinky)
│  │  ├─ stm32f4xx_it.c          ← interrupt handlers (SysTick drives HAL_Delay)
│  │  ├─ stm32f4xx_hal_msp.c     ← HAL low-level init hooks
│  │  └─ system_stm32f4xx.c      ← CMSIS system init (leave alone)
│  └─ Startup\
│     └─ startup_stm32f407xx.s   ← vector table + reset (leave alone)
├─ User\
│  ├─ Inc\                       ← ★ put your own headers here (mymodule.h)
│  └─ Src\                       ← ★ put your own .c modules here (mymodule.c)
└─ STM32F407VGTX_FLASH.ld        ← linker script (1 MB flash @0x08000000, 128 KB RAM)
```

**Rule of thumb:**
- Edit **`Core/Src/main.c`** for your main logic.
- Add extra modules as **`User/Src/*.c`** + **`User/Inc/*.h`** — the build picks
  them up automatically (it globs `Core/Src` and `User/Src`). **No Makefile edits
  needed** when you add a file.
- Leave the startup file, linker script, and `system_stm32f4xx.c` alone.

## E1. The simplest edit: change `main.c`

Out of the box, `project/Core/Src/main.c` is a **board‑agnostic blinky**: it runs
the chip on its internal 16 MHz oscillator (no external crystal needed, so it works
on any F407 board) and "chases" the four Discovery LEDs (PD12→PD13→PD14→PD15),
incrementing two `volatile` counters you can watch over SWD:

```c
volatile uint32_t g_blink_count = 0;   /* ++ on every LED step       */
volatile uint32_t g_led_index   = 0;   /* which LED is lit (0..3)    */
```

To make your first change, open `main.c` and, for example, change the blink speed —
find this line in the `while(1)` loop:

```c
    HAL_Delay(200);     /* milliseconds between LED steps */
```

Change `200` to `1000` (one second). Save. That's it — proceed to PART F to build.

> ℹ️ The default clock is the conservative 16 MHz HSI with **no PLL**. For real
> projects that need full 168 MHz, replace `SystemClock_Config()` with a proper PLL
> configuration for your board's crystal.

## E2. Loading code FROM an existing STM32CubeIDE project

Say you (or someone) already made a project in the STM32CubeIDE graphical editor —
it lives in a **workspace** folder (the one CubeIDE asked you to pick on launch),
e.g. `C:\Users\angel\STM32CubeIDE\workspace_1.x\MyRobotFirmware\`. You want to
build/flash it through this template instead. You don't import the whole IDE
project — you just **copy the source files** into the template's `project\` tree.

A CubeIDE project has the same shape as this template's `project\` folder. Map it
like this:

| In the CubeIDE project… | …copy into the template at |
|-------------------------|----------------------------|
| `Core\Src\main.c` | `project\Core\Src\main.c` (overwrite) |
| `Core\Src\*.c` you wrote (e.g. extra init) | `project\Core\Src\` |
| `Core\Inc\main.h`, your `*.h` | `project\Core\Inc\` |
| `Core\Inc\stm32f4xx_hal_conf.h` | `project\Core\Inc\stm32f4xx_hal_conf.h` (overwrite — this enables your peripherals) |
| any application modules you wrote | `project\User\Src\` and `project\User\Inc\` |

**Steps:**

1. **Close STM32CubeIDE** (so no files are locked).
2. Copy the files per the table above. The fastest way:

   ```powershell
   $src = "C:\Users\angel\STM32CubeIDE\workspace_1.0\MyRobotFirmware"   # <-- your project
   $dst = "C:\Development\STM32TemplateProject\project"

   Copy-Item "$src\Core\Src\main.c"               "$dst\Core\Src\"  -Force
   Copy-Item "$src\Core\Inc\main.h"               "$dst\Core\Inc\"  -Force
   Copy-Item "$src\Core\Inc\stm32f4xx_hal_conf.h" "$dst\Core\Inc\"  -Force
   # copy any extra sources you wrote (NOT the auto-generated HAL — that comes from the pack):
   Copy-Item "$src\Core\Src\stm32f4xx_it.c"       "$dst\Core\Src\"  -Force
   Copy-Item "$src\Core\Src\stm32f4xx_hal_msp.c"  "$dst\Core\Src\"  -Force
   ```

3. **Do NOT copy** the IDE project's `Drivers\` folder (HAL/CMSIS) — this template
   pulls those from the shared firmware pack (PART A2) automatically. Copying them
   would create duplicate symbols.
4. **Do NOT copy** the IDE project's `.cproject`, `.project`, `.ld`, or startup
   `.s` files **unless** your chip differs from `STM32F407VG`. The template already
   has the right linker script and startup file for this board.
5. If your CubeIDE project targeted a **different chip**, see [PART J](#part-j--retargeting-a-different-chip).

> **Why this works:** the IDE‑generated `main.c` and `stm32f4xx_hal_conf.h` are
> plain HAL C code — they don't depend on the IDE. As long as the template compiles
> the same HAL sources (it does, from the pack) and has matching include paths (it
> does), the code builds identically. The template essentially *replaces the IDE's
> build system* with Make/CMake.

After copying, jump to PART F and build.

## E3. Turning peripherals on

The file **`project\Core\Inc\stm32f4xx_hal_conf.h`** controls which HAL modules get
compiled in, via lines like:

```c
#define HAL_UART_MODULE_ENABLED
#define HAL_TIM_MODULE_ENABLED
/* #define HAL_I2C_MODULE_ENABLED */   /* <- commented out = OFF */
```

- The build compiles **all** HAL `.c` files by default (unused ones become harmless
  empty objects), so to use a peripheral you usually just **uncomment its
  `#define`** here — no Makefile changes.
- If you call a HAL function whose module is **disabled** here, the **link will
  fail** with an "undefined reference" error. The fix is to enable that module in
  this header.

---

# PART F — Build the firmware

Open PowerShell in the project root:

```powershell
cd C:\Development\STM32TemplateProject
```

## F1. Build with GNU Make (the simple path)

```powershell
make
```

(If you didn't set up PATH in PART D, use the full `…\make.exe` path instead.)

What happens: it compiles your sources + the whole HAL, links them, and runs
`objcopy` to produce three files in `build\`. At the end it prints the size:

```
   text    data     bss     dec     hex filename
   4328      20    1572    5920    1720 build/stm32app.elf
```

- **text** = code + constants that live in flash
- **data** = initialized variables (copied to RAM at boot)
- **bss** = zero‑initialized variables in RAM

You now have:

```
build\stm32app.elf   ← full image with debug symbols (for SWD/GDB)
build\stm32app.hex   ← Intel HEX (has addresses baked in)
build\stm32app.bin   ← raw binary (flashed to 0x08000000)
build\stm32app.map   ← memory map (what landed where)
```

**Other Make targets:**

```powershell
make            # build .elf/.hex/.bin (default)
make size       # just print section sizes
make clean      # delete the build\ folder
make flash      # build, then upload to the board (PART G)
make erase      # mass-erase the chip's flash
make reset      # hardware-reset the board
make print-CONFIG   # show the resolved configuration
```

## F2. Build with CMake + Ninja (optional, produces identical firmware)

```powershell
$cmake = "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.cmake.win32_1.1.101.202603101401/tools/bin/cmake.exe"

& $cmake -S . -B build-cmake -G Ninja -DCMAKE_TOOLCHAIN_FILE=cmake/gcc-arm-none-eabi.cmake
& $cmake --build build-cmake
```

(Use your real `cmake.exe` path from PART C1. Ninja is found automatically because
CMake's toolchain bundle includes it; if not, add the ninja `tools\bin` to PATH.)

Outputs land in `build-cmake\` (`stm32app.elf/.hex/.bin`). Make and CMake are
verified to produce **identical firmware size** — use whichever you prefer. The
rest of this guide uses the Make path.

---

# PART G — Connect & flash the board

## G1. Plug in the board

1. Connect the **mini‑USB** port (labelled near the ST‑LINK, top of the board) to
   your PC. **Not** the micro‑USB at the bottom.
2. Two red LEDs should light: **PWR** (power) and **COM/LD1** (ST‑LINK, may blink).
3. (Optional) Confirm Windows sees it — in PowerShell:

   ```powershell
   & "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506/tools/bin/STM32_Programmer_CLI.exe" -l
   ```

   `-l` lists connected ST‑LINK probes. You should see your probe's serial number.
   (Use your real `STM32_Programmer_CLI.exe` path from PART C1.)

## G2. Flash it

The one‑liner (build first if you haven't):

```powershell
cd C:\Development\STM32TemplateProject
make flash
```

Under the hood `make flash` runs:

```
STM32_Programmer_CLI.exe -c port=SWD freq=4000 -w build\stm32app.bin 0x08000000 -v -rst
```

…which means: *connect over **SWD** at 4 MHz, **w**rite the `.bin` to flash starting
at `0x08000000`, **v**erify it, then **rst** (reset) so the new firmware starts
running.* You'll see progress like:

```
Memory Programming ...
File          : stm32app.bin
Size          : 4.28 KB
Download in Progress: [==================================================] 100%
File download complete
Verifying ...
Download verified successfully
```

> **`-v` already verified the write** (it reads flash back and compares to your
> file). If you see "Download verified successfully", the bytes on the chip match
> your binary — that's verification step #1 done.

**Flash settings** (interface, speed, address, verify on/off) come from the
`flash` block of `stm32.config.json` and the `FLASH_*` variables in `config.mk`.
Defaults: SWD, 4000 kHz, `0x08000000`, verify on, reset+run after.

---

# PART H — Verify it actually works

Three independent ways to confirm the firmware is alive on the board, from
"look at it" to "read its memory."

## H1. Look at the LEDs (the obvious one)

With the default blinky firmware running, the four user LEDs (green PD12, orange
PD13, red PD14, blue PD15) light **one at a time, chasing in a ring**, stepping
every 200 ms (or whatever delay you set in E1). If you see the chase, it works.

## H2. Read a live variable over SWD (proof it's executing)

The blinky keeps a `volatile uint32_t g_blink_count` that increments on every LED
step. Read it **without halting the board** using the programmer's HOTPLUG mode.
The MCP exposes this as `read_memory` (PART I), but you can also do it directly.

First find the variable's address from the ELF (the bundled `arm-none-eabi-nm`):

```powershell
$gccbin = "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/tools/bin"
& "$gccbin/arm-none-eabi-nm.exe" build\stm32app.elf | Select-String "g_blink_count"
```

That prints an address like `20000004 D g_blink_count`. Read that location twice,
a second apart, and watch it climb:

```powershell
$cli = "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506/tools/bin/STM32_Programmer_CLI.exe"
& $cli -c port=SWD freq=4000 mode=HOTPLUG -r32 0x20000004 1
# wait a second, run it again — the value should be larger.
```

`mode=HOTPLUG` attaches to the **running** target without resetting it, so you're
reading the live counter. If the number grows between reads, your code is genuinely
executing on silicon. ✅

> The MCP tools `read_memory`/`live_memory_*` automate exactly this (by symbol name,
> with continuous polling). See PART I.

## H3. Serial messages (if your firmware prints over UART/VCP)

The default blinky doesn't print anything, but if your firmware sends text over a
UART wired to the ST‑LINK Virtual COM Port (VCP), you can watch it:

1. Find the COM port in **Device Manager → Ports (COM & LPT)** → "STMicroelectronics
   STLink Virtual COM Port (COMx)".
2. Open it at the configured baud (default **115200**) with any serial terminal
   (PuTTY, Tera Term, the Arduino Serial Monitor, or the MCP `serial_*` tools).

---

# PART I — The MCP / agent path (optional)

This is the automation layer: a Python **MCP server** that exposes the whole
create→write→build→flash→verify pipeline as tools an AI agent (or any MCP client
like Claude Desktop) can call. **You do not need this to build and flash by hand** —
it's for driving the board programmatically.

## I1. Install the server's Python deps

```powershell
cd C:\Development\STM32TemplateProject\mcp
python -m venv .venv            # optional but recommended
.\.venv\Scripts\Activate.ps1    # activates the venv (run each session)
pip install -r requirements.txt # installs: mcp, pyserial
```

(`pyserial` powers the `serial_*` tools. The server still starts without it; those
tools just return a clear "not installed" message.)

## I2. Smoke‑test it

```powershell
python smoke_test.py
```

This exercises the server's create/build path locally. You can also just run
`python stm32_mcp_server.py` — it will sit and wait for an MCP client to connect
over stdio (Ctrl‑C to quit).

## I3. Register it with your MCP client

Merge the example from `mcp\claude_desktop_config.example.json` into your client's
MCP config. For **Claude Desktop** that's
`%APPDATA%\Claude\claude_desktop_config.json`:

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

Restart the client; the `stm32-template` tools appear.

## I4. The tools you get

| Tool | What it does |
|------|--------------|
| `get_config` | Resolved config + discovered tool paths + a `toolchain_ok` flag. **Run this first** to confirm the environment. |
| `discover_toolchain_tool(ide_root="")` | Locate gcc/make/cmake/ninja/programmer in a CubeIDE install. |
| `create_project(name, dest_parent, overwrite=False)` | Clone the whole template to `<dest_parent>/<name>`. Returns `project_dir`. |
| `write_source(project_dir, rel_path, content)` | Write/overwrite a file under `project/` (e.g. `Core/Src/main.c`). |
| `read_source(project_dir, rel_path)` | Read a file back. |
| `list_sources(project_dir)` | List everything under `project/`. |
| `build(project_dir, system="make", jobs=8, clean_first=False)` | Compile+link → `.elf/.hex/.bin`; returns artifacts + size. |
| `list_artifacts(project_dir, system="make")` | Paths to the latest build outputs. |
| `flash(project_dir, system="make", binary="bin")` | Upload via `STM32_Programmer_CLI` over ST‑LINK/SWD. |
| `build_and_flash(project_dir, system="make", jobs=8)` | Build then flash in one call (flashes only if the build succeeds). |
| `erase(project_dir="")` / `reset(project_dir="")` | Mass‑erase / hardware‑reset the MCU. |
| `clean(project_dir, system="make")` | Remove the build dir. |
| `serial_list_ports()` | List COM ports; flags ST‑LINK VCP ports (USB VID `0x0483`). |
| `serial_connect(port, baud=0)` / `serial_send(port, data, …)` / `serial_read(port, …)` / `serial_disconnect(port)` | Talk to the board over its VCP/UART. |
| `read_memory(address|symbol, project_dir, …, count, width)` | Read live RAM/peripherals of a **running** target over SWD (by address or ELF symbol). |
| `write_memory(value, address|symbol, …)` | Write live memory of a running target over SWD. |
| `live_memory_start(variables, project_dir, interval_ms=500, …)` | Stream variables continuously via a persistent OpenOCD (no halt) → `session_id` + a JSONL log. |
| `live_memory_read(session_id, last_n=10)` | Most recent samples from a live session's ring buffer. |
| `live_memory_stop(session_id)` | Stop the session, kill OpenOCD, release the ST‑LINK. |

## I5. A typical end‑to‑end agent flow

```
create_project(name="leg_ctrl", dest_parent="C:/robot/fw")  ->  project_dir
write_source(project_dir, "Core/Src/main.c", "<generated firmware>")
write_source(project_dir, "User/Src/motor.c", "...")        # optional modules
build_and_flash(project_dir)                                # -> programs the MCU
live_memory_start('["g_blink_count","g_led_index"]', project_dir=project_dir, interval_ms=250)
#   ... watch the counters move on the running board ...
live_memory_stop(session_id)
```

## I6. ⚠️ Two important live‑monitoring rules

1. **A live session OWNS the ST‑LINK.** You must `live_memory_stop(session_id)`
   before you `flash`, `read_memory`, or `write_memory` — only one thing can drive
   the probe at a time. (A serial VCP connection and SWD memory access *can* run
   together; they use separate USB interfaces.)
2. **OpenOCD config gotcha (already handled, don't change it):** live monitoring
   uses ST's **`interface/stlink-dap.cfg`** (the `dapdirect` driver). The older
   `hla` `stlink.cfg` trips an *"infinite eval recursion"* bug in ST's `swj-dp.tcl`
   with this OpenOCD build. `stm32.config.json → swd.openocd_interface_cfg` is
   already set correctly — leave it.

> ✅ This whole MCP pipeline has been verified end‑to‑end on the **STM32F407G‑DISC1**:
> build → flash → live‑monitor the `g_blink_count` counter incrementing while the
> LED chase runs on PD12–15 → clean release of the probe.

---

# PART J — Retargeting a different chip

Want to use a different STM32F4 part (or board)? Edit, in `stm32.config.json`:

- **`mcu.device` / `mcu.cpu_define`** — e.g. `STM32F411RE` / `STM32F411xE`.
- **`mcu.core` / `mcu.fpu` / `mcu.float_abi`** — only if the core differs
  (Cortex‑M4F is `cortex-m4` + `fpv4-sp-d16` + `hard`).
- **`firmware_pack.path`** — point at the matching `STM32Cube_FW_*` pack.

Then swap two files in `project\`:

- **`Core\Startup\startup_stm32f4xx.s`** — the startup file for the new part (grab
  it from the firmware pack or a CubeMX export).
- **`STM32F407VGTX_FLASH.ld`** — the linker script with the new part's flash/RAM
  sizes.

Finally mirror the MCU flags into `config.mk` (`CPU`, `FPU`, `FLOAT_ABI`,
`CPU_DEFINE`, `LDSCRIPT`, `STARTUP`) and the CMake cache vars in `CMakeLists.txt`.
Both build systems read those values. For families **other than F4**, also update
the CMSIS device‑include subpath. The LED pins in `Core\Inc\main.h` (PD12–15) are
Discovery‑specific — change them for other boards.

---

# Troubleshooting

| Symptom | Likely cause & fix |
|---------|--------------------|
| `make: command not found` / `'make' is not recognized` | PATH not set (PART D), or use the full `…\make.exe` path. |
| `arm-none-eabi-gcc: No such file` | `TOOLCHAIN_BIN` in `config.mk` is wrong. Re‑run `tools\discover_toolchain.ps1` (PART C1) and paste the real `gcc_bin`. |
| Build error: `fatal error: stm32f4xx_hal.h: No such file` | `FW_PACK` path wrong or pack not installed. Check PART A2; confirm the `Test-Path` returns `True`. |
| Link error: `undefined reference to HAL_UART_...` | That HAL module is disabled. Uncomment `#define HAL_UART_MODULE_ENABLED` in `project\Core\Inc\stm32f4xx_hal_conf.h` (PART E3). |
| Makefile recipe fails on `mkdir`/`rm`/`sh` | The **make** plugin's `tools\bin` isn't on PATH — it supplies those Unix helpers. Add it (PART D). |
| `make flash` → "No STLink detected" / "Error: No debug probe detected" | Board not plugged into the **mini‑USB (ST‑LINK)** port, bad cable, or driver issue. Re‑seat cable; check Device Manager (PART A4); run `STM32_Programmer_CLI -l`. |
| Flash works but board does nothing | Did the LEDs chase? If your own firmware needs the PLL/crystal, the default 16 MHz HSI clock setup may be wrong for it — set up `SystemClock_Config()` for your board. |
| `read_memory`/`live_memory_*` fails with "probe busy" | Another tool already owns the ST‑LINK. Stop the live session first (`live_memory_stop`); only one consumer at a time (PART I6). |
| OpenOCD "infinite eval recursion" | You changed `swd.openocd_interface_cfg` away from `interface/stlink-dap.cfg`. Set it back (PART I6). |
| CMake "could not find compiler" | `TOOLCHAIN_BIN` in `cmake\gcc-arm-none-eabi.cmake` (or `-DTOOLCHAIN_BIN=`) is wrong. |
| Duplicate‑symbol link errors after copying from a CubeIDE project | You copied the IDE project's `Drivers\` (HAL/CMSIS) in. Delete those; the template pulls HAL from the pack (PART E2 step 3). |
| Python: `ModuleNotFoundError: mcp` | You didn't `pip install -r requirements.txt`, or you're not in the venv (PART I1). |

---

# One‑page cheat sheet

```powershell
# ── one-time PATH (this session) ───────────────────────────────────────────
$gcc  = "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/tools/bin"
$make = "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.make.win32_2.2.100.202601091506/tools/bin"
$env:PATH = "$gcc;$make;$env:PATH"

# ── everyday workflow ──────────────────────────────────────────────────────
cd C:\Development\STM32TemplateProject
#   1. edit project\Core\Src\main.c  (and project\User\Src\*.c)
make                  # 2. build  -> build\stm32app.elf/.hex/.bin
make flash            # 3. upload + verify + reset (board on mini-USB)
#   4. watch the LEDs chase, or read a live var:
& "$gcc/arm-none-eabi-nm.exe" build\stm32app.elf | Select-String g_blink_count
#      -> read that address with: STM32_Programmer_CLI -c port=SWD mode=HOTPLUG -r32 <addr> 1

# ── housekeeping ───────────────────────────────────────────────────────────
make clean            # delete build\
make erase            # wipe the chip's flash
make print-CONFIG     # show resolved paths/flags
make size             # section sizes
```

**Key file map**

| You want to… | Edit this |
|--------------|-----------|
| Change the program | `project\Core\Src\main.c` |
| Add a code module | `project\User\Src\*.c` + `project\User\Inc\*.h` |
| Turn on a peripheral | `project\Core\Inc\stm32f4xx_hal_conf.h` |
| Change tool paths | `config.mk` (Make) + `stm32.config.json` (MCP) |
| Change flash speed/address | `config.mk` `FLASH_*` / `stm32.config.json` `flash` block |
| Target a different chip | `stm32.config.json` + startup `.s` + `.ld` (PART J) |

---

# Glossary

- **HAL** — Hardware Abstraction Layer: ST's C library of `HAL_*` functions that
  drive the chip's peripherals so you don't poke registers directly.
- **CMSIS** — ARM's standard core‑support headers/code (interrupt vectors, register
  definitions, `SystemInit`).
- **SWD** — Serial Wire Debug: the 2‑wire protocol the ST‑LINK uses to program and
  inspect the chip.
- **ST‑LINK** — the on‑board debugger/programmer (the top half of the DISC1 board);
  also provides a **Virtual COM Port (VCP)** for serial.
- **ELF / HEX / BIN** — build outputs. `.elf` has debug symbols (for SWD/GDB), `.hex`
  and `.bin` are the raw images written to flash.
- **`0x08000000`** — the start address of the STM32's internal flash, where firmware
  is written and from where the chip boots.
- **MCP** — Model Context Protocol: the standard this project's Python server speaks
  so an AI agent can call its build/flash/verify tools.
- **HOTPLUG** — a programmer connect mode that attaches to an **already‑running**
  chip without resetting it — used to peek at live variables.

---

*Generated for `STM32TemplateProject` — target board **STM32F407G‑DISC1**
(STM32F407VG, Cortex‑M4F). Toolchain: GNU Tools for STM32 (GCC 14.3.1) +
STM32CubeProgrammer CLI, bundled in STM32CubeIDE. Build verified with both GNU Make
and CMake+Ninja; flash + live‑memory verify confirmed on real hardware.*
