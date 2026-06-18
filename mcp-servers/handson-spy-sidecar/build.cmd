@echo off
setlocal
cd /d "%~dp0"
dotnet publish -c Release -r win-x64 --self-contained false -o publish
echo Built: publish\handson-spy-sidecar.exe
