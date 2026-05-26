# ============================================================================
#  CMake toolchain file — arm-none-eabi GCC (STM32CubeIDE bundled toolchain)
#  Usage:
#     cmake -S . -B build -G Ninja \
#           -DCMAKE_TOOLCHAIN_FILE=cmake/gcc-arm-none-eabi.cmake \
#           -DTOOLCHAIN_BIN="<.../gnu-tools-for-stm32.../tools/bin>"
# ============================================================================

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

# Path to the bundled toolchain bin. Override with -DTOOLCHAIN_BIN=...
# Default = discovered location on this machine.
set(TOOLCHAIN_BIN "C:/ST/STM32CubeIDE_2.1.1/STM32CubeIDE/plugins/com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.14.3.rel1.win32_1.0.100.202602081740/tools/bin"
    CACHE PATH "Directory containing arm-none-eabi-* executables")

if(WIN32)
  set(TC_EXT ".exe")
else()
  set(TC_EXT "")
endif()

set(CMAKE_C_COMPILER   "${TOOLCHAIN_BIN}/arm-none-eabi-gcc${TC_EXT}")
set(CMAKE_CXX_COMPILER "${TOOLCHAIN_BIN}/arm-none-eabi-g++${TC_EXT}")
set(CMAKE_ASM_COMPILER "${TOOLCHAIN_BIN}/arm-none-eabi-gcc${TC_EXT}")
set(CMAKE_OBJCOPY      "${TOOLCHAIN_BIN}/arm-none-eabi-objcopy${TC_EXT}" CACHE INTERNAL "")
set(CMAKE_SIZE         "${TOOLCHAIN_BIN}/arm-none-eabi-size${TC_EXT}"    CACHE INTERNAL "")

# Don't try to link a full executable during compiler checks (no _start/libc).
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
