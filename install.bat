@echo off
cd /d "c:\Users\SRV\OneDrive\Desktop\New folder\CrewAI\pr-review-bot"
call .venv\Scripts\activate.bat
pip install crewai langchain-openai python-dotenv > install_log.txt 2>&1
echo DONE >> install_log.txt