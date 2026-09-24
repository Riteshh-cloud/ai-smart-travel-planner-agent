import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from agent.planner import TravelAgent

load_dotenv()

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/plan", methods=["POST"])
def plan():
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()

    if not prompt:
        return jsonify({"error": "Please describe your trip first."}), 400

    if not os.getenv("GEMINI_API_KEY"):
        return jsonify({
            "error": "GEMINI_API_KEY is missing. Add it to your local .env file."
        }), 500

    try:
        result = TravelAgent().run(prompt)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

if __name__ == "__main__":
    app.run(debug=True)
