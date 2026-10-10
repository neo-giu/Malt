@echo off
rem Opens Blender with the Malt fork add-on (H:\GameDev\Malt\BlenderMalt, linked from MaltDev) instead of the release add-on in %APPDATA%.
rem Usage: double-click, or drag a .blend onto this file.
set BLENDER_USER_SCRIPTS=H:\GameDev\MaltDev\scripts
start "" "H:\SteamLibrary\steamapps\common\Blender\blender.exe" %*
