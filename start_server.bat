@echo off
echo Starting Excel Processor server...
cd /d "E:\Programming\Trae - MomAutomations"
python -m app.server >nul 2>&1

echo Server started successfully!
echo Access the web interface at: http://localhost:5000
pause
