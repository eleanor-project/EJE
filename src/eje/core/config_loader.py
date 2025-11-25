import yaml
import os
from dotenv import load_dotenv

def load_global_config(config_path):
    # Load environment variables from .env file if it exists
    load_dotenv()

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Override API keys with environment variables if present
    if 'llm' in config and 'api_keys' in config['llm']:
        api_keys = config['llm']['api_keys']

        # Check for environment variables, fall back to config values
        api_keys['openai'] = os.getenv('OPENAI_API_KEY', api_keys.get('openai', ''))
        api_keys['anthropic'] = os.getenv('ANTHROPIC_API_KEY', api_keys.get('anthropic', ''))
        api_keys['gemini'] = os.getenv('GEMINI_API_KEY', api_keys.get('gemini', ''))

    return config
