import os
from google import genai
from dotenv import load_dotenv

def list_gemini_models():
    load_dotenv()
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in .env")
        return
    
    client = genai.Client(api_key=api_key)
    print("Available Gemini Models:")
    try:
        # The new SDK has a models.list() method
        for model in client.models.list():
            print(f"- {model.name} (Supported: {model.supported_actions})")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_gemini_models()
