/**
  ******************************************************************************
  * @file    stm32f4xx_hal_msp.c
  * @brief   HAL MSP (MCU Support Package) module.
  *          Provides MSP init/deinit hooks called by the HAL. The agent adds
  *          peripheral-specific clock/GPIO/DMA/NVIC setup here as needed.
  ******************************************************************************
  */

#include "main.h"

/**
  * @brief  Initializes the Global MSP.
  */
void HAL_MspInit(void)
{
  __HAL_RCC_SYSCFG_CLK_ENABLE();
  __HAL_RCC_PWR_CLK_ENABLE();

  /* System interrupt init — nothing extra needed for the default template. */
}
