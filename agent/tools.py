import requests

def get_weather(city: str) -> dict:
    """Fetch current weather and a short forecast using Open-Meteo."""
    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "language": "en", "format": "json"},
        timeout=10,
    )
    geo.raise_for_status()
    places = geo.json().get("results", [])
    if not places:
        return {"city": city, "error": "City not found"}

    place = places[0]
    lat, lon = place["latitude"], place["longitude"]
    forecast = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,precipitation,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": 3,
            "timezone": "auto",
        },
        timeout=10,
    )
    forecast.raise_for_status()
    data = forecast.json()
    current = data.get("current", {})
    daily = data.get("daily", {})

    return {
        "city": place.get("name", city),
        "country": place.get("country"),
        "temperature_c": current.get("temperature_2m"),
        "precipitation_mm": current.get("precipitation"),
        "wind_kmh": current.get("wind_speed_10m"),
        "weather_code": current.get("weather_code"),
        "forecast_dates": daily.get("time", []),
        "max_temp_c": daily.get("temperature_2m_max", []),
        "min_temp_c": daily.get("temperature_2m_min", []),
        "rain_probability_percent": daily.get("precipitation_probability_max", []),
    }

def calculate_budget(total_budget: float, days: int, travelers: int) -> dict:
    """Create a simple daily and category budget allocation."""
    total_budget = float(total_budget)
    days = max(int(days), 1)
    travelers = max(int(travelers), 1)

    allocation = {
        "stay": round(total_budget * 0.35, 2),
        "food": round(total_budget * 0.20, 2),
        "transport": round(total_budget * 0.20, 2),
        "activities": round(total_budget * 0.15, 2),
        "buffer": round(total_budget * 0.10, 2),
    }

    return {
        "total_budget": total_budget,
        "days": days,
        "travelers": travelers,
        "per_person": round(total_budget / travelers, 2),
        "per_day": round(total_budget / days, 2),
        "allocation": allocation,
        "daily_target_per_person": round(total_budget / days / travelers, 2),
    }

ATTRACTIONS = {
    "vizag": [
        "RK Beach", "Kailasagiri", "Yarada Beach", "INS Kurusura Submarine Museum",
        "Araku Valley day trip", "Dolphin's Nose"
    ],
    "visakhapatnam": [
        "RK Beach", "Kailasagiri", "Yarada Beach", "INS Kurusura Submarine Museum",
        "Araku Valley day trip", "Dolphin's Nose"
    ],
    "hyderabad": [
        "Charminar", "Golconda Fort", "Salar Jung Museum", "Hussain Sagar",
        "Qutb Shahi Tombs", "Birla Mandir"
    ],
    "goa": [
        "Baga Beach", "Fort Aguada", "Candolim", "Anjuna",
        "Fontainhas", "Dudhsagar Falls"
    ],
    "delhi": [
        "India Gate", "Red Fort", "Qutub Minar", "Humayun's Tomb",
        "Lotus Temple", "Akshardham"
    ],
    "mumbai": [
        "Gateway of India", "Marine Drive", "Colaba Causeway",
        "Siddhivinayak Temple", "Elephanta Caves", "Bandra Fort"
    ],
}

def recommend_attractions(city: str, interests: str = "") -> dict:
    key = city.lower().strip()
    places = ATTRACTIONS.get(key)
    if not places:
        places = [
            f"Historic center of {city}",
            f"Popular local market in {city}",
            f"Major viewpoint in {city}",
            f"Local museum or cultural attraction in {city}",
            f"Well-known food district in {city}",
            f"Nearby nature spot around {city}",
        ]

    interest_text = (interests or "").lower()
    if any(word in interest_text for word in ["nature", "beach", "outdoor", "adventure"]):
        places = places[-4:] + places[:2]

    return {
        "city": city,
        "interests": interests,
        "recommended_places": places[:6],
        "note": "Attractions are recommendation data, not live ticket or opening-hour data."
    }

TOOL_DEFINITIONS = [
    {
        "name": "get_weather",
        "description": "Get current weather and a short 3-day forecast for a destination. Use this when weather could affect outdoor activities or packing.",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "Destination city"}},
            "required": ["city"],
        },
    },
    {
        "name": "calculate_budget",
        "description": "Calculate a practical travel budget allocation from total budget, trip length, and number of travelers.",
        "input_schema": {
            "type": "object",
            "properties": {
                "total_budget": {"type": "number", "description": "Total trip budget"},
                "days": {"type": "integer", "description": "Number of trip days"},
                "travelers": {"type": "integer", "description": "Number of travelers"},
            },
            "required": ["total_budget", "days", "travelers"],
        },
    },
    {
        "name": "recommend_attractions",
        "description": "Recommend attractions for a destination based on the user's interests.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "Destination city"},
                "interests": {"type": "string", "description": "Travel interests such as food, nature, history, beaches"},
            },
            "required": ["city"],
        },
    },
]

def execute_tool(name: str, tool_input: dict) -> dict:
    if name == "get_weather":
        return get_weather(**tool_input)
    if name == "calculate_budget":
        return calculate_budget(**tool_input)
    if name == "recommend_attractions":
        return recommend_attractions(**tool_input)
    return {"error": f"Unknown tool: {name}"}
