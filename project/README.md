# `project/` — the STM32F407VG firmware source tree

This is the part the **agent fills in** for each new project. The MCP copies the
whole template, then writes generated source here, then builds and flashes.

```
project/
├─ Core/
│  ├─ Inc/                      # headers
│  │  ├─ main.h                 # entry-point header (LED pin defines for Discovery)
│  │  ├─ stm32f4xx_hal_conf.h   # HAL configuration (which modules are enabled)
│  │  └─ stm32f4xx_it.h
│  ├─ Src/
│  │  ├─ main.c                 # << OVERWRITE THIS per project (default = blinky)
│  │  ├─ stm32f4xx_it.c         # interrupt handlers (SysTick drives HAL_Delay)
│  │  ├─ stm32f4xx_hal_msp.c    # HAL MSP hooks
│  │  └─ system_stm32f4xx.c     # CMSIS system init (from the firmware pack)
│  └─ Startup/
│     └─ startup_stm32f407xx.s  # vector table + reset handler (from the pack)
├─ User/                        # put application modules here (User/Src, User/Inc)
│  ├─ Inc/
│  └─ Src/
├─ Drivers/                     # empty by default — HAL/CMSIS are referenced from
│                               # the firmware pack. Run tools/vendor_hal.ps1 to
│                               # copy them in here for a self-contained project.
└─ STM32F407VGTX_FLASH.ld       # linker script (1M FLASH @0x08000000, 128K RAM)
```

## What's fixed vs. what the agent changes

| Fixed (infrastructure)                          | Agent-authored (per project)        |
|-------------------------------------------------|-------------------------------------|
| linker script, startup, `system_stm32f4xx.c`    | `Core/Src/main.c` and any           |
| `stm32f4xx_hal_conf.h`, IT/MSP skeletons        | `User/Src/*.c`, `User/Inc/*.h`      |
| HAL/CMSIS driver sources (from the pack)         | extra peripheral init, app logic    |

## Enabling peripherals

`Core/Inc/stm32f4xx_hal_conf.h` controls which HAL modules are compiled in
(`#define HAL_xxx_MODULE_ENABLED`). The build compiles **all** HAL `.c` files by
default (unused ones become empty objects), so enabling a module there is enough —
no Makefile edits needed. If the agent calls a HAL function whose module is
*disabled* in this header, the link will fail; enable it here.

## Default firmware

Out of the box `main.c` is a board-agnostic blinky (HSI 16 MHz, no PLL, toggles
PD12 — the green LED on the STM32F4-Discovery). It exists only to prove the
build+flash pipeline; replace it with real firmware.
