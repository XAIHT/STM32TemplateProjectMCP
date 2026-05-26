# ============================================================================
#  config.mk  —  Make-side defaults for STM32TemplateProject (STM32F407VG)
#
#  These mirror stm32.config.json so `make` works standalone (no MCP needed).
#  Everything here can be overridden on the command line, e.g.:
#     make TOOLCHAIN_BIN=/path/to/bin FW_PACK=/path/to/pack
#  The MCP passes the JSON values the same way.
# ============================================================================

# ---- Project ---------------------------------------------------------------
PROJECT      ?= stm32app
SRC_DIR      ?= project
BUILD        ?= build

# ---- Target MCU ------------------------------------------------------------
CPU          ?= cortex-m4
FPU          ?= fpv4-sp-d16
FLOAT_ABI    ?= hard
CPU_DEFINE   ?= STM32F407xx
LDSCRIPT     ?= $(SRC_DIR)/STM32F407VGTX_FLASH.ld
STARTUP      ?= $(SRC_DIR)/Core/Startup/startup_stm32f407xx.s

# ---- Bundled toolchain (discovered on this machine) ------------------------
# Set TOOLCHAIN_BIN empty to use whatever arm-none-eabi-* is on PATH.
TOOLCHAIN_BIN ?= C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/tools/bin
PROGRAMMER    ?= C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32_2.2.400.202601091506/tools/bin/STM32_Programmer_CLI.exe

# ---- Firmware pack (HAL + CMSIS sources, referenced not copied) ------------
FW_PACK      ?= C:/Users/angel/STM32Cube/Repository/STM32Cube_FW_F4_V1.28.3
HAL_DIR      ?= $(FW_PACK)/Drivers/STM32F4xx_HAL_Driver
CMSIS_DIR    ?= $(FW_PACK)/Drivers/CMSIS

# ---- HAL source selection --------------------------------------------------
# COMPILE_ALL_HAL=1 -> build every HAL .c (bulletproof; unused = empty object).
# COMPILE_ALL_HAL=0 -> build only $(HAL_SOURCES) listed below (faster).
COMPILE_ALL_HAL ?= 1
HAL_SOURCES_MINIMAL := \
  stm32f4xx_hal.c stm32f4xx_hal_cortex.c stm32f4xx_hal_rcc.c stm32f4xx_hal_rcc_ex.c \
  stm32f4xx_hal_gpio.c stm32f4xx_hal_dma.c stm32f4xx_hal_dma_ex.c \
  stm32f4xx_hal_pwr.c stm32f4xx_hal_pwr_ex.c \
  stm32f4xx_hal_flash.c stm32f4xx_hal_flash_ex.c stm32f4xx_hal_flash_ramfunc.c \
  stm32f4xx_hal_exti.c

# ---- Build options ---------------------------------------------------------
OPT          ?= -Og
DEBUG        ?= 1
C_STD        ?= gnu11

# ---- Flash options (STM32_Programmer_CLI / ST-LINK) ------------------------
FLASH_PORT   ?= SWD
FLASH_FREQ   ?= 4000
FLASH_ADDR   ?= 0x08000000
