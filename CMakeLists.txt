# ============================================================================
#  STM32TemplateProject — CMake build (STM32F407VG, HAL, arm-none-eabi)
#
#  Configure + build (Ninja, using the IDE's bundled cmake/ninja):
#     cmake -S . -B build -G Ninja \
#           -DCMAKE_TOOLCHAIN_FILE=cmake/gcc-arm-none-eabi.cmake
#     cmake --build build
#
#  Produces build/<name>.elf, .hex, .bin and prints size.
#  The MCP can also drive this; otherwise the Makefile is the simpler path.
# ============================================================================
cmake_minimum_required(VERSION 3.22)

# ---- Configurable cache variables (mirror stm32.config.json) ---------------
set(PROJECT_NAME    "stm32app"                         CACHE STRING "Output name")
set(SRC_DIR         "${CMAKE_SOURCE_DIR}/project"      CACHE PATH   "Project source root")
set(MCU_CORE        "cortex-m4"                         CACHE STRING "")
set(MCU_FPU         "fpv4-sp-d16"                       CACHE STRING "")
set(MCU_FLOAT_ABI   "hard"                              CACHE STRING "")
set(MCU_DEFINE      "STM32F407xx"                       CACHE STRING "")
set(LINKER_SCRIPT   "${SRC_DIR}/STM32F407VGTX_FLASH.ld" CACHE FILEPATH "")
set(STARTUP_FILE    "${SRC_DIR}/Core/Startup/startup_stm32f407xx.s" CACHE FILEPATH "")
set(FW_PACK         "C:/Users/angel/STM32Cube/Repository/STM32Cube_FW_F4_V1.28.3" CACHE PATH "")
set(COMPILE_ALL_HAL ON CACHE BOOL "Compile every HAL .c (bulletproof) vs a minimal set")
set(OPT_LEVEL       "-Og"                               CACHE STRING "")

enable_language(C ASM)
project(${PROJECT_NAME} C ASM)

set(HAL_DIR   "${FW_PACK}/Drivers/STM32F4xx_HAL_Driver")
set(CMSIS_DIR "${FW_PACK}/Drivers/CMSIS")

# ---- Sources ---------------------------------------------------------------
file(GLOB CORE_SRC  "${SRC_DIR}/Core/Src/*.c")
file(GLOB USER_SRC  "${SRC_DIR}/User/Src/*.c")

if(COMPILE_ALL_HAL)
  file(GLOB HAL_SRC "${HAL_DIR}/Src/*.c")
  list(FILTER HAL_SRC EXCLUDE REGEX ".*_template\\.c$")
else()
  set(HAL_SRC
    "${HAL_DIR}/Src/stm32f4xx_hal.c"
    "${HAL_DIR}/Src/stm32f4xx_hal_cortex.c"
    "${HAL_DIR}/Src/stm32f4xx_hal_rcc.c"
    "${HAL_DIR}/Src/stm32f4xx_hal_rcc_ex.c"
    "${HAL_DIR}/Src/stm32f4xx_hal_gpio.c"
    "${HAL_DIR}/Src/stm32f4xx_hal_dma.c"
    "${HAL_DIR}/Src/stm32f4xx_hal_dma_ex.c"
    "${HAL_DIR}/Src/stm32f4xx_hal_pwr.c"
    "${HAL_DIR}/Src/stm32f4xx_hal_pwr_ex.c"
    "${HAL_DIR}/Src/stm32f4xx_hal_flash.c"
    "${HAL_DIR}/Src/stm32f4xx_hal_flash_ex.c"
    "${HAL_DIR}/Src/stm32f4xx_hal_flash_ramfunc.c"
    "${HAL_DIR}/Src/stm32f4xx_hal_exti.c")
endif()

set(SOURCES ${CORE_SRC} ${USER_SRC} ${HAL_SRC} ${STARTUP_FILE})

add_executable(${PROJECT_NAME}.elf ${SOURCES})

target_include_directories(${PROJECT_NAME}.elf PRIVATE
  "${SRC_DIR}/Core/Inc"
  "${SRC_DIR}/User/Inc"
  "${HAL_DIR}/Inc"
  "${HAL_DIR}/Inc/Legacy"
  "${CMSIS_DIR}/Device/ST/STM32F4xx/Include"
  "${CMSIS_DIR}/Include")

target_compile_definitions(${PROJECT_NAME}.elf PRIVATE USE_HAL_DRIVER ${MCU_DEFINE})

set(MCU_FLAGS -mcpu=${MCU_CORE} -mthumb -mfpu=${MCU_FPU} -mfloat-abi=${MCU_FLOAT_ABI})

target_compile_options(${PROJECT_NAME}.elf PRIVATE
  ${MCU_FLAGS} ${OPT_LEVEL} -g3 -Wall
  -fdata-sections -ffunction-sections
  $<$<COMPILE_LANGUAGE:C>:-std=gnu11>
  $<$<COMPILE_LANGUAGE:ASM>:-x$<SEMICOLON>assembler-with-cpp>)

target_link_options(${PROJECT_NAME}.elf PRIVATE
  ${MCU_FLAGS}
  -T${LINKER_SCRIPT}
  -specs=nano.specs -specs=nosys.specs
  -Wl,-Map=${PROJECT_NAME}.map,--cref
  -Wl,--gc-sections
  -Wl,--no-warn-rwx-segments
  -lc -lm -lnosys)

# ---- Post-build: .hex, .bin, size ------------------------------------------
add_custom_command(TARGET ${PROJECT_NAME}.elf POST_BUILD
  COMMAND ${CMAKE_OBJCOPY} -O ihex   $<TARGET_FILE:${PROJECT_NAME}.elf> ${PROJECT_NAME}.hex
  COMMAND ${CMAKE_OBJCOPY} -O binary -S $<TARGET_FILE:${PROJECT_NAME}.elf> ${PROJECT_NAME}.bin
  COMMAND ${CMAKE_SIZE} $<TARGET_FILE:${PROJECT_NAME}.elf>
  COMMENT "Generating .hex / .bin and size")
