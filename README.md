# AdaptiveTrip AI — Constraint-Aware Autonomous Travel Planning Agent

AdaptiveTrip AI is a college project that demonstrates an **agentic AI workflow** rather than a simple chatbot.

The user gives a travel request in natural language. The LLM decides which tools are required, receives tool results, creates a draft itinerary, and passes that draft through a deterministic constraint checker. If a conflict is detected, the agent sends the conflict back to the LLM and generates a corrected itinerary.

## Architecture

```text
User Request
     |
     v
LLM Planning Agent
     |
     |---- chooses Weather Tool
     |---- chooses Budget Tool
     |---- chooses Attraction Tool
     |
     v
Tool Results
     |
     v
Draft Itinerary
     |
     v
Constraint Checker
     |
   conflict?
   /      \
 yes       no
  |         |
  v         v
LLM Replan  Final Itinerary
```

## Why it is agentic

The application uses Anthropic's tool-use interface. The Python program does **not** call every tool before asking the LLM for a plan. Instead, the model can request only the tools it considers useful. The application executes those requested tools and returns their results to the model.

After the first plan, a separate deterministic constraint layer checks for examples such as:
- high rain probability + outdoor-heavy schedule
- very low budget + premium/luxury accommodation
- estimated spend substantially above the user's budget

When a conflict is found, the LLM is asked to replan.

## Tools

1. `get_weather` — Open-Meteo current weather + short forecast
2. `calculate_budget` — daily/per-person/category allocation
3. `recommend_attractions` — destination attraction recommendations

## Tech Stack

- Python
- Flask
- Anthropic Claude API
- Native LLM tool calling
- Open-Meteo API
- HTML / CSS / JavaScript

## Run locally

### 1. Create a virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the API key

Create a file named `.env` in the project root:

```env
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-sonnet-4-6
```

Never upload `.env` or an API key to GitHub.

### 4. Start the application

```bash
python app.py
```

Open the local Flask URL shown in the terminal, normally:

```text
http://127.0.0.1:5000
```

## Demo prompt

```text
Plan a 3-day Goa trip for 2 people with a budget of ₹18000.
We like beaches, food and photography. Check the weather and
keep indoor alternatives.
```

## What to explain during review

**Problem:** Generic travel chatbots often produce static plans that do not react to constraints.

**Solution:** AdaptiveTrip AI combines LLM reasoning, tool selection and deterministic validation. It can change the itinerary when a constraint is violated.

**Unique part:** The important feature is the **constraint → validation → replanning loop**, not just generating an itinerary.

**Trace:** The UI shows which tools the LLM selected and when the constraint checker triggered replanning.

## Important limitation

Attraction recommendations are local project data and weather comes from Open-Meteo. The application does not provide live hotel booking, ticket booking, or guaranteed prices.
