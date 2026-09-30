import os
import time

from dotenv import load_dotenv
from google import genai


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)


def ask_gemini(question, business_context):

    prompt = f"""
You are a Business Intelligence analyst.

You are analyzing the Olist Brazilian e-commerce dataset.

Here is the business data available to you:

{business_context}

Answer the user's question using only the business data provided above.

Give a clear, concise business-oriented answer.
If useful, provide recommendations based on the data.
Do not invent numbers that are not provided.

User question:
{question}
"""

    for attempt in range(3):

        try:

            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt
            )

            return response.text

        except Exception as e:

            if "503" in str(e) and attempt < 2:

                time.sleep(2 ** attempt)

            else:

                raise e