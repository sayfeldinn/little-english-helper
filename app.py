"""
app.py
------
Flask application entry point.

Routes:
    GET  /        -> renders the main page (templates/index.html)
    POST /check   -> receives {"sentence": "..."} JSON, returns {"feedback": "..."}

All AI-specific logic lives in services/ai_service.py. This file only deals
with HTTP concerns: parsing requests, validating input, and returning JSON
responses / error codes.
"""

import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from services.ai_service import AIService

# Load variables from .env into the process environment (e.g. GEMINI_API_KEY).
load_dotenv()

app = Flask(__name__)

# Create a single shared AIService instance for the whole app.
ai_service = AIService()

# Reasonable limit to stop someone from sending a huge wall of text
# (protects both our API costs and the user's experience).
MAX_SENTENCE_LENGTH = 500


@app.route("/")
def index():
    """Renders the main (and only) page of the app."""
    return render_template("index.html")


@app.route("/check", methods=["POST"])
def check_sentence():
    """
    Accepts a JSON body: {"sentence": "..."}
    Returns:      {"feedback": "..."}  on success  (HTTP 200)
             or   {"error": "..."}     on failure   (HTTP 4xx/5xx)
    """
    # --- 1. Validate that we actually received JSON ---
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Please send a valid JSON request."}), 400

    sentence = data.get("sentence", "")

    # --- 2. Validate the sentence itself ---
    if not isinstance(sentence, str):
        return jsonify({"error": "The 'sentence' field must be text."}), 400

    sentence = sentence.strip()

    if not sentence:
        return jsonify({"error": "Please type a sentence before checking it! ✏️"}), 400

    if len(sentence) > MAX_SENTENCE_LENGTH:
        return jsonify({
            "error": f"That sentence is a bit too long! Please keep it under "
                     f"{MAX_SENTENCE_LENGTH} characters."
        }), 400

    # --- 3. Ask the AI service for feedback, translating errors to friendly messages ---
    try:
        result = ai_service.get_feedback(sentence)
        return jsonify(result), 200

    except ValueError:
        # Service wasn't configured with an API key at all.
        return jsonify({
            "error": "The server is not configured correctly (missing API key). "
                     "Please contact the site administrator."
        }), 500

    except PermissionError:
        return jsonify({
            "error": "The AI service rejected our request (invalid API key). "
                     "Please contact the site administrator."
        }), 401

    except LookupError:
        return jsonify({
            "error": "We're getting a lot of requests right now! Please wait a "
                     "moment and try again. ⏳"
        }), 429

    except TimeoutError:
        return jsonify({
            "error": "The AI teacher is taking too long to answer. Please try again."
        }), 504

    except ConnectionError:
        return jsonify({
            "error": "We couldn't connect to the AI service. Please check your "
                     "internet connection and try again. 🌐"
        }), 503

    except RuntimeError as exc:
        # Log the real error server-side for debugging, but keep the
        # user-facing message friendly and non-technical.
        app.logger.error("AI service error: %s", exc)
        return jsonify({
            "error": "Something went wrong on our end. Please try again in a bit."
        }), 502

    except Exception as exc:  # noqa: BLE001 - absolute last resort safety net
        app.logger.exception("Unexpected error in /check: %s", exc)
        return jsonify({
            "error": "An unexpected error occurred. Please try again. 😅"
        }), 500


if __name__ == "__main__":
    # debug=True is convenient for local development; turn this off in production.
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
