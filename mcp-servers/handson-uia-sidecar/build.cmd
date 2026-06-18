@echo off
dotnet publish -c Release -r win-x64 --self-contained false -o publish
echo Sidecar built to publish\handson-uia-sidecar.exe
