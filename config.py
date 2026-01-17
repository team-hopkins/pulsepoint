"""Configuration management for CarePoint AI System"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Arize Configuration
ARIZE_SPACE_KEY = os.getenv("ARIZE_SPACE_KEY")
ARIZE_API_KEY = os.getenv("ARIZE_API_KEY")
PROJECT_NAME = os.getenv("PROJECT_NAME", "pulsepoint")

# Phoenix Cloud Configuration (for Experiments & Datasets)
PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY", ARIZE_API_KEY)  # Can use same Arize API key
PHOENIX_COLLECTOR_ENDPOINT = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "https://app.phoenix.arize.com")

# Application Settings
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Model Configuration
DEFAULT_MODEL = "gpt-5-mini"
VISION_MODEL = "gemini-2.0-flash"
MEDICAL_MODEL = "claude-sonnet-4.5"

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "carepoint_medical")

# Digital Ocean Spaces Configuration
SPACES_ACCESS_KEY = os.getenv("SPACES_ACCESS_KEY")
SPACES_SECRET_KEY = os.getenv("SPACES_SECRET_KEY")
SPACES_REGION = os.getenv("SPACES_REGION", "nyc3")
SPACES_BUCKET = os.getenv("SPACES_BUCKET", "carepoint-medical-images")

# Urgency Thresholds
HIGH_STAKES_KEYWORDS = [
    "chest pain", "can't breathe", "unconscious", "severe bleeding",
    "stroke", "heart attack", "anaphylaxis", "choking", "seizure"
]
