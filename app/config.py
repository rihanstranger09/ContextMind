"""Local .env support. Real environment variables take precedence; secrets never logged."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=False)

_PROVIDERS = ('disabled', 'openai', 'cohere')
_KEY_ENV = {'openai': 'OPENAI_API_KEY', 'cohere': 'COHERE_API_KEY'}
_DEFAULT_MODEL = {'openai': 'gpt-4o-mini', 'cohere': 'command-a-03-2025', 'disabled': 'gpt-4o-mini'}


def llm_config():
    provider = os.getenv('LLM_PROVIDER', 'disabled').strip().lower()
    if provider not in _PROVIDERS:
        raise ValueError('LLM_PROVIDER must be openai, cohere or disabled')
    model = os.getenv('MODEL_NAME', '').strip() or _DEFAULT_MODEL[provider]
    if not model or len(model) > 100:
        raise ValueError('Invalid MODEL_NAME')
    key_env = _KEY_ENV.get(provider, 'OPENAI_API_KEY')
    return {'provider': provider, 'model': model,
            'api_key': os.getenv(key_env, '').strip(), 'api_key_env': key_env}
