<#
.SYNOPSIS
  Locate the toolchain/programmer/build executables bundled inside a
  STM32CubeIDE installation by globbing its plugins directory.

.DESCRIPTION
  Plugin folder names are version-stamped and change with each IDE update, so
  hard-coding them is fragile. This script finds them dynamically and prints a
  JSON object (also usable to refresh the "toolchain" block of stm32.config.json).

.PARAMETER IdeRoot
  Path to the STM32CubeIDE install root (the folder containing stm32cubeide.exe).

.EXAMPLE
  pwsh -File tools/discover_toolchain.ps1 -IdeRoot 'C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE'
#>
param(
  [string]$IdeRoot = 'C:\ST\STM32CubeIDE_2.1.1\STM32CubeIDE'
)

$ErrorActionPreference = 'Stop'
$plugins = Join-Path $IdeRoot 'plugins'
if (-not (Test-Path $plugins)) { throw "Plugins dir not found: $plugins" }

function Find-First([string]$pattern, [string]$subpath) {
  $dir = Get-ChildItem -Path $plugins -Directory -Filter $pattern |
         Sort-Object Name -Descending | Select-Object -First 1
  if ($null -eq $dir) { return $null }
  $p = Join-Path $dir.FullName $subpath
  if (Test-Path $p) { return ($p -replace '\\','/') } else { return $null }
}

$result = [ordered]@{
  ide_root       = ($IdeRoot -replace '\\','/')
  gcc_bin        = Find-First 'com.st.stm32cube.ide.mcu.externaltools.gnu-tools-for-stm32.*win32*' 'tools/bin'
  make_bin       = Find-First 'com.st.stm32cube.ide.mcu.externaltools.make.win32*'  'tools/bin'
  cmake_bin      = Find-First 'com.st.stm32cube.ide.mcu.externaltools.cmake.win32*' 'tools/bin'
  ninja_bin      = Find-First 'com.st.stm32cube.ide.mcu.externaltools.ninja.win32*' 'tools/bin'
  programmer_cli = Find-First 'com.st.stm32cube.ide.mcu.externaltools.cubeprogrammer.win32*' 'tools/bin/STM32_Programmer_CLI.exe'
  openocd_bin    = Find-First 'com.st.stm32cube.ide.mcu.externaltools.openocd.win32*' 'tools/bin'
}

$result | ConvertTo-Json -Depth 4
