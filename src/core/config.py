"""
Lab 11 — Configuration & API Key Setup
"""
import os
from dotenv import load_dotenv


def setup_api_key():
    """Load OpenAI API key from .env file or environment."""
    # Tải biến môi trường từ file .env
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))
    
    if "OPENAI_API_KEY" not in os.environ:
        print("Error: OPENAI_API_KEY not found in environment variables.")
        # os.environ["OPENAI_API_KEY"] = input("Enter OpenAI API Key: ")
    print("OpenAI API key loaded.")


# Allowed banking topics (used by topic_filter)
ALLOWED_TOPICS = [
    "banking", "account", "transaction", "transfer",
    "loan", "interest", "savings", "credit",
    "deposit", "withdrawal", "balance", "payment",
    "tai khoan", "giao dich", "tiet kiem", "lai suat",
    "chuyen tien", "the tin dung", "so du", "vay",
    "ngan hang", "atm",
]

# Blocked topics (immediate reject)
BLOCKED_TOPICS = [
    "hack", "exploit", "weapon", "drug", "illegal",
    "violence", "gambling", "bomb", "kill", "steal",
]
