@echo off
echo 正在安装依赖...
pip install flask pillow pyinstaller pynput pyaudio pywin32 requests
echo 正在打包主控端为 EXE...
pyinstaller --onefile --name ChimeraController --windowed MasterFinal.py
echo 完成！EXE 在 dist 文件夹里
pause