import json
from vertexai.generative_models import (GenerationConfig, GenerativeModel, Part)
import vertexai
import config

# --- Configure Vertex AI ---
PROJECT_ID = config.PROJECT_ID
LOCATION = config.LOCATION


def analyze_media_with_gemini(media_uri, mime_type): # New function name
    """Analyzes media (image or video) with Gemini."""
    try:
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        model = GenerativeModel("gemini-1.5-pro-002")  # Or your chosen model

        response_schema = { #This can remain the same
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "brand": {"type": "string"},
                    "model": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "description": {"type": "string"},
                    "timestamp": {"type": "string"}, # you might adjust this if you are dealing with images.
                },
                "required": ["item", "quantity", "description", "timestamp"], # And this
            },
        }


        response = model.generate_content(
            [
              """You are an insurance adjuster creating a home inventory. Analyze this media and return a JSON array of objects, each describing an item seen. 
                 
                 Include item, brand, model (if possible), quantity, and brief description of the item.  
                 
                 Only include items that are clearly visible and fully within the frame. 
                 
                 Exclude partially visible or ambiguous objects. 
                 
                 For each item, include relevant information such as timestamps (for videos) or location within the image (for images).""", # Slightly improved prompt
              Part.from_uri(media_uri, mime_type=mime_type),  # Use mime_type
            ],
            generation_config=GenerationConfig(
                response_mime_type="application/json", response_schema=response_schema
            ),
        )
        return response.text
    except Exception as e:
        return json.dumps({"error": f"Gemini API call failed: {e}"})