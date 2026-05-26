/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    main.c
  * @brief   Default template firmware — STM32F407VG blinky.
  *
  * PURPOSE: prove that compile -> link -> objcopy -> flash works end to end.
  * The MCP / Super-agent replaces this file with generated firmware.
  *
  * Clock: runs on the internal HSI (16 MHz) with NO PLL, so it is correct on
  * *any* STM32F407VG board regardless of the external crystal. Replace
  * SystemClock_Config() with a proper PLL configuration for production use.
  ******************************************************************************
  */
/* USER CODE END Header */

/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Observable state — kept in RAM (.data/.bss) and `volatile` so it is never
 * optimized away. The MCP's live_memory_* / read_memory tools watch these over
 * SWD to prove the firmware is actually running on the board. */
volatile uint32_t g_blink_count = 0;   /* ++ on every LED step                */
volatile uint32_t g_led_index   = 0;   /* which LED is currently lit (0..3)   */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);

/* The four user LEDs on the STM32F407G-DISC1, in chase order. */
static const uint16_t LED_PINS[4] = {
  LED_GREEN_Pin, LED_ORANGE_Pin, LED_RED_Pin, LED_BLUE_Pin
};

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{
  /* Reset of all peripherals, initialize the Flash interface and the Systick. */
  HAL_Init();

  /* Configure the system clock */
  SystemClock_Config();

  /* Initialize configured peripherals */
  MX_GPIO_Init();

  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* Light exactly one LED at a time, chasing around the ring. */
    HAL_GPIO_WritePin(LED_GPIO_Port,
                      LED_GREEN_Pin | LED_ORANGE_Pin | LED_RED_Pin | LED_BLUE_Pin,
                      GPIO_PIN_RESET);
    HAL_GPIO_WritePin(LED_GPIO_Port, LED_PINS[g_led_index], GPIO_PIN_SET);

    g_led_index = (g_led_index + 1U) & 0x3U;
    g_blink_count++;

    HAL_Delay(200);
  }
  /* USER CODE END WHILE */
}

/**
  * @brief System Clock Configuration — HSI 16 MHz, no PLL (board-agnostic).
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};

  __HAL_RCC_PWR_CLK_ENABLE();
  __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

  /* Use the internal 16 MHz oscillator directly. */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK |
                                RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSI;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;
  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_0) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief GPIO Initialization — user LEDs on PD12..PD15.
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  __HAL_RCC_GPIOD_CLK_ENABLE();

  HAL_GPIO_WritePin(LED_GPIO_Port,
                    LED_GREEN_Pin | LED_ORANGE_Pin | LED_RED_Pin | LED_BLUE_Pin,
                    GPIO_PIN_RESET);

  GPIO_InitStruct.Pin = LED_GREEN_Pin | LED_ORANGE_Pin | LED_RED_Pin | LED_BLUE_Pin;
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(LED_GPIO_Port, &GPIO_InitStruct);
}

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  __disable_irq();
  while (1)
  {
  }
}

#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  (void)file;
  (void)line;
}
#endif /* USE_FULL_ASSERT */
