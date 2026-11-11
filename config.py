"""
Configuration module for the Travel Planning Assistant
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# if not ANTHROPIC_API_KEY:
#     raise ValueError("ANTHROPIC_API_KEY not found in environment variables. Please set it in .env file.")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables. Please set it in .env file.")

# Research API Configuration
# Open-Meteo & Country APIs do not require API keys.



# Model Configuration
# MODEL = "claude-sonnet-4-20250514"
# MODEL = "gemini-1.5-flash"
MODEL = "gemini-3.5-flash-lite"

# Application Configuration
APP_NAME = "Travel Planning Assistant"
DEFAULT_CHAT_MODEL = MODEL

# Agent Configuration
AGENT_CONFIG = {
    "intent_agent": {
        "temperature": 0.5,
        "max_tokens": 1000,
    },
    "research_agent": {
        "temperature": 0.6,
        "max_tokens": 1500,
    },
    "itinerary_agent": {
        "temperature": 0.7,
        "max_tokens": 2000,
    },
    "budget_agent": {
        "temperature": 0.5,
        "max_tokens": 1500,
    },
}

# Streamlit Configuration
STREAMLIT_CONFIG = {
    "page_title": APP_NAME,
    "page_icon": "✈️",
    "layout": "wide",
}
