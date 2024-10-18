import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, Tool, grounding
import json
import config

PROJECT_ID = config.PROJECT_ID
LOCATION = config.LOCATION

search_tool = Tool.from_google_search_retrieval(grounding.GoogleSearchRetrieval())

def get_estimated_price(item, brand, descrip):
    """Gets an estimated price using Gemini with Google Search grounding."""
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        model = GenerativeModel("gemini-1.5-flash-002")  # Choose a suitable model (pro for better grounding)

        description = ""
        if brand:
            description += brand
        if item:
            description += f" ({item})"
        if model:
            descrip += f"with the description: ({descrip})"
        if not descrip: #Handle cases where there is no description.
            return None

        prompt = f"What is the typical price of a {description}? If you aren't sure, give a reasonable estimate. Return only the price as a single number (e.g., 25.99)."

        response = model.generate_content(
            prompt,
            tools=[search_tool],
            generation_config=GenerationConfig(temperature=0.0),  # Reduce randomness
        )

        try:
            price = response.text.strip()
            return price
        except ValueError:
            return None

    except Exception as e:
        return None