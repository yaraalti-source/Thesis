@echo off
echo ========================================
echo Finding Your IP Address
echo ========================================
echo.
echo Your local IP addresses:
echo.
ipconfig | findstr /i "IPv4"
echo.
echo ========================================
echo Use the IP address that starts with 192.168.x.x or 10.x.x.x
echo ========================================
echo.
pause

