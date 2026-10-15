@echo off
rem Opens the Pixelizer test copy with the Malt fork add-on, applies one tools\pixelart\scenes.py setup, and stays open.
rem Usage: open_setup.bat [SETUP] [FILE.blend]     default: pixel_pal_kof_l2 on H:\GameDev\Pixelizer\content\malt\testmalt.blend
rem Set PIXEL_LINES_DEBUG=1 first to see the line marker colours (magenta outline, cyan inner, yellow KEEP, orange overlap).
set SETUP=%~1
if "%SETUP%"=="" set SETUP=pixel_pal_kof_l2
set FILE=%~2
if "%FILE%"=="" set FILE=H:\GameDev\Pixelizer\content\malt\testmalt.blend
set BLENDER_USER_SCRIPTS=H:\GameDev\MaltDev\scripts
start "" "H:\SteamLibrary\steamapps\common\Blender\blender.exe" "%FILE%" --python "%~dp0pixelart\open_setup.py" -- %SETUP%
