/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    main.h
  * @brief   Header for main.c — template entry point.
  *
  * This file is part of the STM32TemplateProject scaffold. The Super-agent /
  * MCP is expected to OVERWRITE main.c (and optionally this header) with the
  * generated firmware for each new project. The out-of-the-box content is a
  * minimal blinky used to validate the build + flash pipeline.
  ******************************************************************************
  */
/* USER CODE END Header */

#ifndef __MAIN_H
#define __MAIN_H

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include "stm32f4xx_hal.h"

/* Exported functions prototypes ---------------------------------------------*/
void Error_Handler(void);

/* USER CODE BEGIN Private defines */
/* On the STM32F4-Discovery board the user LEDs are on GPIOD pins 12..15. */
#define LED_GREEN_Pin        GPIO_PIN_12
#define LED_ORANGE_Pin       GPIO_PIN_13
#define LED_RED_Pin          GPIO_PIN_14
#define LED_BLUE_Pin         GPIO_PIN_15
#define LED_GPIO_Port        GPIOD
/* USER CODE END Private defines */

#ifdef __cplusplus
}
#endif

#endif /* __MAIN_H */
