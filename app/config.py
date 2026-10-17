"""Local .env support. Real environment variables take precedence; secrets never logged."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=False)


def llm_config():
    provider = os.getenv('LLM_PROVIDER', 'disabled').strip().lower()
    if provider not in ('disabled', 'openai'):
        raise ValueError('LLM_PROVIDER must be openai or disabled')
    model = os.getenv('MODEL_NAME', 'gpt-4o-mini').strip()
    if not model or len(model) > 100:
        raise ValueError('Invalid MODEL_NAME')
    return {'provider': provider, 'model': model, 'api_key': os.getenv('OPENAI_API_KEY', '').strip()}
