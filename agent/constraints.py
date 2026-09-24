import re


def _extract_budget(text):
    patterns = [
        r"₹\s*([0-9,]+)",
        r"\brs\.?\s*([0-9,]+)",
        r"\binr\s*([0-9,]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text.lower())

        if match:
            return int(match.group(1).replace(",", ""))

    return None


def validate_plan(
    plan_text,
    tool_results=None,
    user_prompt="",
    check_original_request=True
):
    """
    Validate a travel itinerary.

    check_original_request=True:
        Used for the FIRST validation to detect conflicts
        in the user's original request.

    check_original_request=False:
        Used AFTER replanning to verify that the generated
        itinerary itself is realistic.
    """

    conflicts = []

    request = user_prompt.lower()
    plan = plan_text.lower()

    # ---------------------------------------------------------
    # Get budget
    # ---------------------------------------------------------

    budget = _extract_budget(request)

    if budget is None and tool_results:
        budget_result = tool_results.get("calculate_budget")

        if isinstance(budget_result, dict):
            budget = budget_result.get("total_budget")

    # ---------------------------------------------------------
    # INITIAL REQUEST VALIDATION
    # ---------------------------------------------------------

    if check_original_request:

        luxury_requested = any(
            phrase in request
            for phrase in [
                "luxury hotel",
                "luxury hotels",
                "luxury resort",
                "luxury resorts",
                "5-star",
                "5 star",
                "fine dining",
                "expensive restaurant",
                "expensive restaurants",
            ]
        )

        if (
            luxury_requested
            and budget is not None
            and budget <= 10000
        ):
            conflicts.append(
                f"The requested luxury accommodation/fine dining "
                f"is incompatible with the ₹{budget:,} total budget."
            )

    # ---------------------------------------------------------
    # CHECK GENERATED PLAN
    # ---------------------------------------------------------

    if budget is not None and budget <= 10000:

        luxury_in_plan = any(
            phrase in plan
            for phrase in [
                "luxury hotel",
                "luxury hotels",
                "luxury resort",
                "luxury resorts",
                "5-star hotel",
                "5 star hotel",
                "fine dining",
                "expensive restaurant",
                "expensive restaurants",
            ]
        )

        budget_friendly_in_plan = any(
            phrase in plan
            for phrase in [
                "budget hotel",
                "budget stay",
                "budget accommodation",
                "hostel",
                "homestay",
                "guesthouse",
                "local cafe",
                "local café",
                "budget-friendly",
                "budget friendly",
                "low-cost",
                "low cost",
            ]
        )

        # Only flag the revised plan if it STILL contains
        # luxury choices without budget alternatives.
        if (
            luxury_in_plan
            and not budget_friendly_in_plan
        ):
            conflicts.append(
                f"The revised itinerary still contains "
                f"luxury accommodation or expensive dining "
                f"despite the ₹{budget:,} budget."
            )

    # ---------------------------------------------------------
    # WEATHER / OUTDOOR VALIDATION
    # ---------------------------------------------------------

    if check_original_request:

        rain_requested = any(
            phrase in request
            for phrase in [
                "heavy rain",
                "rainy",
                "thunderstorm",
                "showers",
            ]
        )

        outdoor_requested = any(
            phrase in request
            for phrase in [
                "beach",
                "outdoor",
                "trek",
                "hike",
                "water sports",
                "outdoor photography",
            ]
        )

        if rain_requested and outdoor_requested:
            conflicts.append(
                "Outdoor activities may conflict with "
                "rain-sensitive conditions."
            )

    # ---------------------------------------------------------
    # RETURN RESULT
    # ---------------------------------------------------------

    return conflicts