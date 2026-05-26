# ============================================================================
#  STM32TemplateProject  —  GNU Make build (STM32F407VG, HAL, arm-none-eabi)
#
#  Targets:
#     make            build .elf + .hex + .bin (default)
#     make flash      build then upload via STM32_Programmer_CLI (ST-LINK)
#     make erase      mass-erase the chip
#     make size       print section sizes
#     make clean      remove build/
#     make print-CONFIG  show resolved config
#
#  All variables come from config.mk and may be overridden on the command line.
# ============================================================================

include config.mk

# The per-source rules are generated via foreach/eval below, which would
# otherwise make the first generated object the default goal. Pin it to 'all'.
.DEFAULT_GOAL := all

# ---- Toolchain -------------------------------------------------------------
ifeq ($(strip $(TOOLCHAIN_BIN)),)
  PREFIX := arm-none-eabi-
else
  PREFIX := $(TOOLCHAIN_BIN)/arm-none-eabi-
endif

CC      := $(PREFIX)gcc
AS      := $(PREFIX)gcc -x assembler-with-cpp
CP      := $(PREFIX)objcopy
SZ      := $(PREFIX)size

# ---- Sources ---------------------------------------------------------------
# User / application + Core sources (recursively, but flat dirs here)
C_SOURCES  := $(wildcard $(SRC_DIR)/Core/Src/*.c)
C_SOURCES  += $(wildcard $(SRC_DIR)/User/Src/*.c)

# HAL sources from the firmware pack (referenced in place)
ifeq ($(COMPILE_ALL_HAL),1)
  HAL_C := $(filter-out %_template.c,$(wildcard $(HAL_DIR)/Src/*.c))
else
  HAL_C := $(addprefix $(HAL_DIR)/Src/,$(HAL_SOURCES_MINIMAL))
endif
C_SOURCES += $(HAL_C)

ASM_SOURCES := $(STARTUP)

# ---- Includes --------------------------------------------------------------
C_INCLUDES := \
  -I$(SRC_DIR)/Core/Inc \
  -I$(SRC_DIR)/User/Inc \
  -I$(HAL_DIR)/Inc \
  -I$(HAL_DIR)/Inc/Legacy \
  -I$(CMSIS_DIR)/Device/ST/STM32F4xx/Include \
  -I$(CMSIS_DIR)/Include

# ---- Defines ---------------------------------------------------------------
C_DEFS := -DUSE_HAL_DRIVER -D$(CPU_DEFINE)

# ---- Flags -----------------------------------------------------------------
MCU := -mcpu=$(CPU) -mthumb -mfpu=$(FPU) -mfloat-abi=$(FLOAT_ABI)

ifeq ($(DEBUG),1)
  DBG := -g3 -gdwarf-2
else
  DBG :=
endif

CFLAGS  := $(MCU) $(C_DEFS) $(C_INCLUDES) $(OPT) $(DBG) -std=$(C_STD) \
           -Wall -fdata-sections -ffunction-sections
ASFLAGS := $(MCU) $(OPT) $(DBG) -Wall -fdata-sections -ffunction-sections

# Dependency generation is added per-recipe (needs $@, which is only defined
# inside a rule). Do NOT bake it into CFLAGS with ':=' or $@ expands empty.
DEPFLAGS = -MMD -MP -MF$(@:%.o=%.d)

LDFLAGS := $(MCU) -specs=nano.specs -specs=nosys.specs -T$(LDSCRIPT) \
           -Wl,-Map=$(BUILD)/$(PROJECT).map,--cref -Wl,--gc-sections \
           -Wl,--no-warn-rwx-segments \
           -lc -lm -lnosys

# ---- Objects (flat, in $(BUILD)) -------------------------------------------
# NOTE: we deliberately avoid `vpath`, because GNU make splits search paths on
# ':' and would mangle absolute Windows paths (e.g. C:/Users/...). Instead we
# generate one explicit rule per source via foreach/eval. Object names are flat
# (by basename); all source basenames in this template are unique.
OBJECTS := $(addprefix $(BUILD)/,$(notdir $(C_SOURCES:.c=.o)))
OBJECTS += $(addprefix $(BUILD)/,$(notdir $(ASM_SOURCES:.s=.o)))

define COMPILE_C_RULE
$(BUILD)/$(notdir $(1:.c=.o)): $(1) | $(BUILD)
	$$(CC) -c $$(CFLAGS) $$(DEPFLAGS) $$< -o $$@
endef
define COMPILE_S_RULE
$(BUILD)/$(notdir $(1:.s=.o)): $(1) | $(BUILD)
	$$(AS) -c $$(ASFLAGS) $$< -o $$@
endef
$(foreach src,$(C_SOURCES),$(eval $(call COMPILE_C_RULE,$(src))))
$(foreach src,$(ASM_SOURCES),$(eval $(call COMPILE_S_RULE,$(src))))

# ============================================================================
.PHONY: all flash erase reset size clean print-CONFIG

all: $(BUILD)/$(PROJECT).elf $(BUILD)/$(PROJECT).hex $(BUILD)/$(PROJECT).bin size

$(BUILD)/$(PROJECT).elf: $(OBJECTS)
	$(CC) $(OBJECTS) $(LDFLAGS) -o $@

$(BUILD)/%.hex: $(BUILD)/%.elf
	$(CP) -O ihex $< $@

$(BUILD)/%.bin: $(BUILD)/%.elf
	$(CP) -O binary -S $< $@

$(BUILD):
	@mkdir -p $@

size: $(BUILD)/$(PROJECT).elf
	$(SZ) $<

# ---- Flash / erase via STM32CubeProgrammer CLI (ST-LINK) -------------------
flash: $(BUILD)/$(PROJECT).bin
	"$(PROGRAMMER)" -c port=$(FLASH_PORT) freq=$(FLASH_FREQ) -w $< $(FLASH_ADDR) -v -rst

erase:
	"$(PROGRAMMER)" -c port=$(FLASH_PORT) freq=$(FLASH_FREQ) -e all

reset:
	"$(PROGRAMMER)" -c port=$(FLASH_PORT) freq=$(FLASH_FREQ) -rst

clean:
	@rm -rf $(BUILD)

print-CONFIG:
	@echo "PROJECT     = $(PROJECT)"
	@echo "MCU flags   = $(MCU)"
	@echo "CC          = $(CC)"
	@echo "FW_PACK     = $(FW_PACK)"
	@echo "HAL sources = $(words $(HAL_C)) files (COMPILE_ALL_HAL=$(COMPILE_ALL_HAL))"
	@echo "LDSCRIPT    = $(LDSCRIPT)"
	@echo "PROGRAMMER  = $(PROGRAMMER)"

# Pull in auto-generated dependencies
-include $(wildcard $(BUILD)/*.d)
