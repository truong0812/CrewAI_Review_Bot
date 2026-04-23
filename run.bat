@echo off
cd /d "c:\Users\SRV\OneDrive\Desktop\New folder\CrewAI\pr-review-bot"
call .venv\Scripts\activate.bat
python main.py %*
pause