import os
from pydantic import BaseModel

from dotenv import load_dotenv

load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")


class ExtractedFact(BaseModel):
    field: str
    value: str
    unit: str


print("=== LLM API READINESS TEST ===")

# 1. OPENAI TEST
if not openai_key:
    print("OPENAI_API: NOT_CONFIGURED (OPENAI_API_KEY not set in environment)")
    print("STRUCTURED_OUTPUT: BLOCKED (Key needed before H0)")
    print("MODEL: gpt-5-mini (Configured in .env.example)")
else:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=openai_key)
        model_name = os.getenv("OPENAI_MODEL", "gpt-5-mini")

        # Test structured output
        try:
            completion = client.beta.chat.completions.parse(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Extract the specified business fact.",
                    },
                    {
                        "role": "user",
                        "content": 'Extract the following business fact: "Contract value is ₹41.6 lakh."',
                    },
                ],
                response_format=ExtractedFact,
                temperature=0,
            )
        except Exception as e:
            if "model" in str(e).lower() or "not found" in str(e).lower():
                print(
                    f"Notice: '{model_name}' not available on account tier, falling back to 'gpt-4o-mini'..."
                )
                model_name = "gpt-4o-mini"
                completion = client.beta.chat.completions.parse(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "Extract the specified business fact.",
                        },
                        {
                            "role": "user",
                            "content": 'Extract the following business fact: "Contract value is ₹41.6 lakh."',
                        },
                    ],
                    response_format=ExtractedFact,
                    temperature=0,
                )
            else:
                raise

        parsed = completion.choices[0].message.parsed
        print("OPENAI_API: PASS")
        print(f"STRUCTURED_OUTPUT: PASS (Parsed: {parsed})")
        print(f"MODEL: {model_name}")
    except Exception as e:
        print(f"OPENAI_API: FAIL ({e})")
        print("STRUCTURED_OUTPUT: FAIL")

# 2. GEMINI TEST
if not gemini_key:
    print("GEMINI: NOT_CONFIGURED (GEMINI_API_KEY not set in environment)")
    print("FALLBACK_STATUS: NOT_CONFIGURED (Non-blocking fallback)")
else:
    try:
        from google import genai

        client = genai.Client(api_key=gemini_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        try:
            response = client.models.generate_content(
                model=model_name,
                contents='Extract value: "Contract value is 41.6 lakh."',
            )
        except Exception as e:
            print(f"Exception trying {model_name}: {e}")
            raise

        print("GEMINI: PASS")
        print(f"FALLBACK_STATUS: PASS (Model: {model_name})")
        preview = (
            response.text[:60].encode("ascii", errors="replace").decode()
            if response.text
            else "None"
        )
        print(f"Response preview: {preview}")

    except Exception as e:
        print(f"GEMINI: FAIL ({e})")
        print("FALLBACK_STATUS: FAIL")
