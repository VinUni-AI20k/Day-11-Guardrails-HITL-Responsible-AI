"""
Lab 11 — Configuration & API Key Setup
"""
import os
from pathlib import Path


DEFAULT_OPENAI_MODEL = "openai/gpt-4.1-mini"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def load_dotenv_file(dotenv_path: str | Path | None = None, override: bool = False) -> Path:
    """Load simple KEY=value pairs from the repo .env file into os.environ."""
    env_path = Path(dotenv_path) if dotenv_path else _project_root() / ".env"
    if not env_path.exists():
        return env_path

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = _strip_quotes(value.strip())
        if key and (override or key not in os.environ):
            os.environ[key] = value

    return env_path


def get_llm_provider() -> str:
    """Return the active LLM provider.

    Preference order:
    1. Explicit LLM_PROVIDER env var
    2. OPENAI_API_KEY if present
    3. GOOGLE_API_KEY if present
    4. Default to OpenAI
    """
    load_dotenv_file()

    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if provider in {"openai", "google"}:
        return provider
    model = os.getenv("MODEL", "").strip().lower()
    if model.startswith("openai/") or model.startswith("gpt-"):
        return "openai"
    if model.startswith("gemini"):
        return "google"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("GOOGLE_API_KEY"):
        return "google"
    return "openai"


def get_default_model_name() -> str:
    """Return the default model name for the active provider."""
    load_dotenv_file()

    model = os.getenv("MODEL", "").strip()
    if model:
        return model

    if get_llm_provider() == "openai":
        return os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    return os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)


def build_adk_model():
    """Build an ADK-compatible model object/string for the active provider."""
    load_dotenv_file()
    provider = get_llm_provider()
    if provider == "openai":
        try:
            from google.adk.models.lite_llm import LiteLlm
        except ImportError as exc:
            raise ImportError(
                "OpenAI mode requires LiteLLM support from google-adk. "
                "Please ensure your environment is up to date."
            ) from exc

        try:
            import litellm  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "OpenAI mode requires the 'litellm' package. "
                "Install it with: pip install litellm"
            ) from exc

        return LiteLlm(model=get_default_model_name())

    return get_default_model_name()


def setup_api_key():
    """Load the API key for the active provider from .env or prompt."""
    load_dotenv_file()
    provider = get_llm_provider()

    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY", "").strip():
            os.environ["OPENAI_API_KEY"] = input("Enter OpenAI API Key: ")
        print(f"API key loaded for OpenAI ({get_default_model_name()}).")
        return

    if not os.getenv("GOOGLE_API_KEY", "").strip():
        os.environ["GOOGLE_API_KEY"] = input("Enter Google API Key: ")
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "0"
    print(f"API key loaded for Google ({get_default_model_name()}).")


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
