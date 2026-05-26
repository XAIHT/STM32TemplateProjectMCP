<#
.SYNOPSIS
  Copy (vendor) the HAL driver + CMSIS sources from the STM32Cube firmware pack
  INTO this project's project/Drivers tree, making the project fully
  self-contained (no longer dependent on the shared firmware pack location).

.DESCRIPTION
  By default the template REFERENCES the firmware pack in place (small project
  copies). Run this once if you need a portable, archival, or version-pinned
  copy. After vendoring, point the build at the local Drivers tree by setting
  FW_PACK to the project root and adjusting the include subpaths, OR keep using
  the pack — vendoring is optional.

.PARAMETER ProjectRoot
  The template/project root (folder containing 'project' and stm32.config.json).

.PARAMETER FwPack
  Path to the STM32Cube_FW_F4 firmware pack.
#>
param(
  [string]$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
  [string]$FwPack      = 'C:\Users\angel\STM32Cube\Repository\STM32Cube_FW_F4_V1.28.3'
)

$ErrorActionPreference = 'Stop'
$dst = Join-Path $ProjectRoot 'project\Drivers'

$halSrc   = Join-Path $FwPack 'Drivers\STM32F4xx_HAL_Driver'
$cmsisSrc = Join-Path $FwPack 'Drivers\CMSIS'

Write-Host "Vendoring HAL + CMSIS from:`n  $FwPack`n into:`n  $dst" -ForegroundColor Cyan

New-Item -ItemType Directory -Force -Path (Join-Path $dst 'STM32F4xx_HAL_Driver') | Out-Null
Copy-Item -Recurse -Force (Join-Path $halSrc 'Inc') (Join-Path $dst 'STM32F4xx_HAL_Driver\Inc')
Copy-Item -Recurse -Force (Join-Path $halSrc 'Src') (Join-Path $dst 'STM32F4xx_HAL_Driver\Src')

# CMSIS: only the bits we actually need (core + F4 device headers).
New-Item -ItemType Directory -Force -Path (Join-Path $dst 'CMSIS\Include') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dst 'CMSIS\Device\ST\STM32F4xx\Include') | Out-Null
Copy-Item -Recurse -Force (Join-Path $cmsisSrc 'Include\*') (Join-Path $dst 'CMSIS\Include')
Copy-Item -Recurse -Force (Join-Path $cmsisSrc 'Device\ST\STM32F4xx\Include\*') (Join-Path $dst 'CMSIS\Device\ST\STM32F4xx\Include')

Write-Host "Done. To build against the vendored tree, set in stm32.config.json / config.mk:" -ForegroundColor Green
Write-Host "  FW_PACK    -> $ProjectRoot/project   (and HAL_DIR=Drivers/STM32F4xx_HAL_Driver, CMSIS_DIR=Drivers/CMSIS)"
