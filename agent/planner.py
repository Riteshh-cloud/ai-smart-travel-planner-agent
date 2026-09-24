import os

from google import genai
from google.genai import types

from .tools import TOOL_DEFINITIONS, execute_tool
from .constraints import validate_plan


SYSTEM_PROMPT = """
You are AdaptiveTrip AI, an autonomous constraint-aware travel planning agent.

Your job is to transform a user's natural-language travel request into a realistic,
structured itinerary.

IMPORTANT BEHAVIOR:

1. Analyze the user's request and identify:
   - destination
   - duration
   - number of travelers
   - budget
   - interests
   - weather requirements
   - accommodation preferences
   - activity preferences

2. Decide yourself which available tools are useful.

3. Use the weather tool when weather can materially affect the trip.

4. Use the budget tool when the user provides or implies a budget.

5. Use the attraction tool when destination activities or places are needed.

6. Do not invent live weather, prices, tickets, opening hours, or hotel availability.

7. After receiving tool results, create a practical itinerary containing:
   - trip assumptions
   - day-by-day itinerary
   - approximate budget
   - weather-aware advice
   - packing suggestions
   - fallback options for bad weather

8. If the user's requirements are contradictory, prioritize feasibility.

   Example:
   If the user requests luxury hotels and expensive restaurants
   with an extremely small budget, do NOT pretend that the request
   is achievable.

   Instead:
   - identify the conflict
   - replace expensive options with realistic alternatives
   - preserve the user's important interests
   - stay within the requested budget
   - produce a realistic alternative

9. If the system reports a constraint conflict, you MUST replan.

10. During replanning, actually change the itinerary.
    Do not merely explain the conflict.

11. Return a complete corrected itinerary after replanning.

12. Keep the response concise enough for a college project demonstration.
"""


def convert_tools():
    """
    Convert the project's tool definitions into Gemini
    function-calling format.
    """

    gemini_tools = []

    for tool in TOOL_DEFINITIONS:
        gemini_tools.append(
            types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["input_schema"],
            )
        )

    return [
        types.Tool(
            function_declarations=gemini_tools
        )
    ]


class TravelAgent:

    def __init__(self):

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is missing. "
                "Add it to your local .env file."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.5-flash-lite"
        )

        self.tools = convert_tools()

    # =========================================================
    # GEMINI TOOL-USING LOOP
    # =========================================================

    def _agent_loop(
        self,
        contents,
        trace,
        tool_results
    ):

        for _ in range(8):

            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=self.tools,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                ),
            )

            function_calls = response.function_calls

            # -------------------------------------------------
            # Gemini has finished using tools
            # -------------------------------------------------

            if not function_calls:

                return response.text.strip(), contents

            # -------------------------------------------------
            # Preserve Gemini's tool-call response
            # -------------------------------------------------

            contents.append(
                response.candidates[0].content
            )

            function_response_parts = []

            # -------------------------------------------------
            # Execute each tool selected by Gemini
            # -------------------------------------------------

            for call in function_calls:

                tool_name = call.name

                tool_input = dict(
                    call.args or {}
                )

                trace.append(
                    {
                        "step": len(trace) + 1,
                        "action": f"LLM selected {tool_name}",
                        "details": tool_input,
                    }
                )

                # Execute local application tool
                result = execute_tool(
                    tool_name,
                    tool_input
                )

                # Save result for constraint validation
                tool_results[tool_name] = result

                # Send result back to Gemini
                function_response_parts.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response=result
                    )
                )

            contents.append(
                types.Content(
                    role="user",
                    parts=function_response_parts
                )
            )

        raise RuntimeError(
            "Agent exceeded the maximum tool-use steps."
        )

    # =========================================================
    # MAIN TRAVEL AGENT
    # =========================================================

    def run(self, user_prompt: str) -> dict:

        # -----------------------------------------------------
        # Initialize execution trace
        # -----------------------------------------------------

        trace = [
            {
                "step": 1,
                "action": "Received travel request",
                "details": user_prompt,
            }
        ]

        # Store results returned by tools
        tool_results = {}

        # -----------------------------------------------------
        # Initial conversation
        # -----------------------------------------------------

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=user_prompt
                    )
                ],
            )
        ]

        # =====================================================
        # FIRST PLANNING CYCLE
        # =====================================================

        draft, contents = self._agent_loop(
            contents,
            trace,
            tool_results
        )

        trace.append(
            {
                "step": len(trace) + 1,
                "action": "Generated draft itinerary",
                "details": (
                    "Gemini produced a plan after "
                    "selecting and executing tools."
                ),
            }
        )

        # =====================================================
        # INITIAL CONSTRAINT CHECK
        #
        # This checks the ORIGINAL USER REQUEST.
        #
        # Example:
        # ₹5,000 + luxury hotels = conflict
        # =====================================================

        conflicts = validate_plan(
            draft,
            tool_results,
            user_prompt,
            check_original_request=True
        )

        # Number of autonomous replanning cycles
        replans = 0

        # =====================================================
        # AUTONOMOUS REPLANNING LOOP
        # =====================================================

        while conflicts and replans < 2:

            replans += 1

            # -------------------------------------------------
            # Record detected conflict
            # -------------------------------------------------

            trace.append(
                {
                    "step": len(trace) + 1,
                    "action": "Constraint checker found conflict",
                    "details": conflicts,
                }
            )

            # -------------------------------------------------
            # Convert conflicts into readable text
            # -------------------------------------------------

            conflict_text = "\n".join(
                f"- {item}"
                for item in conflicts
            )

            # -------------------------------------------------
            # Ask Gemini to autonomously replan
            # -------------------------------------------------

            replan_prompt = f"""
The deterministic constraint checker detected the
following conflict in the current itinerary:

{conflict_text}

ORIGINAL USER REQUEST:

{user_prompt}

You must now autonomously REPLAN the trip.

Requirements:

1. Keep the destination, duration, number of travelers,
   and important interests whenever possible.

2. Resolve the detected constraint conflict.

3. If the requested luxury accommodation or expensive
   dining cannot fit the budget, replace it with realistic
   budget-friendly alternatives.

4. Do NOT simply explain the conflict.

5. Actually change the itinerary.

6. Keep estimated spending within the user's requested budget.

7. Preserve the user's main interests where possible.

8. Return a COMPLETE revised itinerary.

9. Include:
   - trip assumptions
   - day-by-day itinerary
   - budget allocation
   - weather advice
   - packing suggestions
   - fallback options

The revised itinerary should be realistic and internally consistent.
"""

            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text=replan_prompt
                        )
                    ],
                )
            )

            # -------------------------------------------------
            # Run Gemini again
            # -------------------------------------------------

            draft, contents = self._agent_loop(
                contents,
                trace,
                tool_results
            )

            # -------------------------------------------------
            # Record successful replan
            # -------------------------------------------------

            trace.append(
                {
                    "step": len(trace) + 1,
                    "action": "Replanned itinerary",
                    "details": (
                        f"Autonomous replanning cycle "
                        f"{replans} completed."
                    ),
                }
            )

            # =================================================
            # SECOND VALIDATION
            #
            # IMPORTANT:
            # We now check the GENERATED PLAN itself.
            #
            # We do NOT keep treating the original impossible
            # request as a new conflict.
            # =================================================

            conflicts = validate_plan(
                draft,
                tool_results,
                user_prompt,
                check_original_request=False
            )

        # =====================================================
        # FINAL VALIDATION
        # =====================================================

        if conflicts:

            final_validation = conflicts

        else:

            final_validation = (
                "No unresolved constraint conflict."
            )

        trace.append(
            {
                "step": len(trace) + 1,
                "action": "Final validation",
                "details": final_validation,
            }
        )

        # =====================================================
        # FINAL RESULT
        # =====================================================

        return {
            "plan": draft,

            "trace": trace,

            "replanned": replans > 0,

            "remaining_conflicts": conflicts,

            "tools_used": list(
                tool_results.keys()
            ),

            "model": self.model,
        }