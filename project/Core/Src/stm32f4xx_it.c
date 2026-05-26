/**
  ******************************************************************************
  * @file    stm32f4xx_it.c
  * @brief   Cortex-M4 and STM32F4 interrupt service routines.
  ******************************************************************************
  */

#include "main.h"
#include "stm32f4xx_it.h"

/* External: HAL time-base handle declared in stm32f4xx_hal.c */

/******************************************************************************/
/*           Cortex-M4 Processor Interruption and Exception Handlers          */
/******************************************************************************/

void NMI_Handler(void)
{
  while (1) { }
}

void HardFault_Handler(void)
{
  while (1) { }
}

void MemManage_Handler(void)
{
  while (1) { }
}

void BusFault_Handler(void)
{
  while (1) { }
}

void UsageFault_Handler(void)
{
  while (1) { }
}

void SVC_Handler(void)
{
}

void DebugMon_Handler(void)
{
}

void PendSV_Handler(void)
{
}

/**
  * @brief  System tick timer — drives HAL_Delay / HAL time base.
  */
void SysTick_Handler(void)
{
  HAL_IncTick();
}

/******************************************************************************/
/* STM32F4 Peripheral Interrupt Handlers                                      */
/* Add peripheral handlers below (e.g. USART2_IRQHandler).                    */
/******************************************************************************/
