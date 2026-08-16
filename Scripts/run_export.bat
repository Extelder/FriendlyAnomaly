@echo off
rem Export all meshes + textures without opening the editor.
rem Output: <project>\Exported\  (same folder structure as Content Browser)

set ENGINE=H:\UE_5.3\Engine\Binaries\Win64\UnrealEditor-Cmd.exe
set PROJECT=C:\Users\The Witcher\Documents\Unreal Projects\FriendlyAnomaly\FriendlyAnomaly.uproject
set SCRIPT=C:\Users\The Witcher\Documents\Unreal Projects\FriendlyAnomaly\Scripts\export_assets.py

"%ENGINE%" "%PROJECT%" -run=pythonscript -script="%SCRIPT%" -stdout -unattended -nullrhi

echo.
echo Done. Check the "Exported" folder next to the .uproject
pause
