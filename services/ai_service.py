"""
ai_service.py
--------------
This module contains the AIService class using Google Gemini.

Responsibilities:
- Build the system + user prompts used for grading a child's sentence.
- Call the Gemini API safely, with timeouts.
- Translate any provider-specific errors into friendly, predictable
  exceptions that app.py can catch and turn into JSON error responses.
"""

import os
import httpx
from google import genai
from google.genai import types
from google.genai import errors as genai_errors


class AIService:
    """
    Wraps all communication with the Google Gemini API.

    Responsibilities:
    - Build the system + user prompts used for grading a child's sentence.
    - Call the Gemini API safely, with timeouts.
    - Translate any provider-specific errors into friendly, predictable
      exceptions that app.py can catch and turn into JSON error responses.
    """

    MODEL_NAME = "gemini-2.5-flash-lite"

    TEMPERATURE = 0.3

    MAX_TOKENS = 150

    REQUEST_TIMEOUT_SECONDS = 15

    SYSTEM_PROMPT = (
        "You are a friendly English teacher for young children aged 6-10. "
        "Always:\n"
        "- encourage the child first\n"
        "- politely correct any mistakes\n"
        "- explain the mistake in very simple English\n"
        "- ask one short question to practice the corrected grammar or vocabulary\n"
        "- keep your response under 80 words\n"
        "- never criticize\n"
        "- always use positive, warm language\n"
        "If the input is not a real English sentence (e.g. gibberish, only "
        "numbers, only emojis, or another language), gently ask the child "
        "to try writing a simple English sentence, in a kind and "
        "encouraging tone — do not pretend to correct grammar that isn't "
        "there.\n\n"
        "You MUST format your response exactly like this:\n"
        "For a real English sentence:\n"
        "CORRECTED: <the corrected sentence, with no extra text>\n"
        "FEEDBACK: <your encouragement, corrections, and suggestions>\n"
        "For nonsense or gibberish, ONLY output:\n"
        "FEEDBACK: <ask the child to write a real English sentence>"
    )

    def __init__(self, api_key: str | None = None):
        """
        api_key: if not provided, will look for the GEMINI_API_KEY
        environment variable (loaded via .env).
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

        if not self.api_key:
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

    @staticmethod
    def _build_user_prompt(sentence: str) -> str:
        """Builds the user-facing prompt sent to the model."""
        return (
            f'Analyze this child\'s English sentence:\n\n"{sentence}"\n\n'
            "Provide feedback following the instructions."
        )

    def get_feedback(self, sentence: str) -> dict:
        """
        Sends the sentence to the Gemini model and returns a dict:
            {"feedback": "...", "corrected_sentence": "..."}

        Raises:
            ValueError: if the service was never configured with an API key.
            TimeoutError: if the request took too long.
            ConnectionError: if we couldn't reach the API (no internet, DNS, etc).
            PermissionError: if the API key is invalid/unauthorized.
            LookupError: if we hit a rate limit.
            RuntimeError: for any other unexpected API error.
        """
        if self.client is None:
            raise ValueError("AI service is not configured: missing API key.")

        try:
            response = self.client.models.generate_content(
                model=self.MODEL_NAME,
                contents=self._build_user_prompt(sentence),
                config=types.GenerateContentConfig(
                    system_instruction=self.SYSTEM_PROMPT,
                    temperature=self.TEMPERATURE,
                    max_output_tokens=self.MAX_TOKENS,
                ),
            )
            raw = response.text
            if not raw:
                return {
                    "feedback": "Great try! Can you try writing your sentence again?",
                    "corrected_sentence": sentence,
                }

            corrected_sentence = ""
            feedback = raw.strip()
            for line in raw.strip().split("\n"):
                if line.upper().startswith("CORRECTED:"):
                    corrected_sentence = line.split(":", 1)[1].strip()
                elif line.upper().startswith("FEEDBACK:"):
                    feedback = line.split(":", 1)[1].strip()

            return {
                "feedback": feedback or "Great try! Keep practicing!",
                "corrected_sentence": corrected_sentence,
            }

        except genai_errors.ClientError as exc:
            if exc.code in (401, 403):
                raise PermissionError("Invalid or missing API key.") from exc
            elif exc.code == 429:
                raise LookupError("Rate limit exceeded. Please try again shortly.") from exc
            else:
                raise RuntimeError(f"AI service returned an error: {exc}") from exc

        except genai_errors.ServerError as exc:
            raise RuntimeError(f"AI service returned an error: {exc}") from exc

        except httpx.TimeoutException as exc:
            raise TimeoutError("The AI service took too long to respond.") from exc

        except httpx.NetworkError as exc:
            raise ConnectionError("Could not reach the AI service.") from exc

        except Exception as exc:
            raise RuntimeError(f"Unexpected error while contacting AI service: {exc}") from exc
