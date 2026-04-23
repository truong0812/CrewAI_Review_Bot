"""Quick test: CrewAI with Groq via env vars."""
import sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

# Set env vars that OpenAI SDK reads natively
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_BASE_URL"] = os.getenv("OPENAI_API_BASE")

model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
print(f"Model: {model}")
print(f"Base URL: {os.environ['OPENAI_BASE_URL']}")

from crewai import Agent, Task, Crew, Process

try:
    agent = Agent(role="Reviewer", goal="Say hello", backstory="You are helpful.", llm=model, verbose=True)
    task = Task(description="Say hello in one sentence.", expected_output="A greeting.", agent=agent)
    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
    print("Running crew...")
    result = crew.kickoff()
    print(f"SUCCESS! Result: {result}")
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()