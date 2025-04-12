import configparser
import os

def load_config(config_path=None):
    # Create a ConfigParser object
    config = configparser.ConfigParser()
    config_path = config_path
    # we can explicitly pass in the config_path, such as in test scripts
    if config_path is None:
            # try to get the configuration file location from the environment variable
        try:
            config_path = os.environ['MEMENTO_CONFIG_PATH']
        except KeyError:
            pass
        # default to the home directory
        config_path = os.path.expanduser('~/memento_config/config.ini')

    config_files = config.read(config_path)
    if config_files is None or len(config_files) == 0:
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    return config

def load_ndex_credentials (config_path=None):
    config = load_config(config_path=config_path)
    username = config.get('NDEX', 'NDEX_USERNAME', fallback=None)
    password = config.get('NDEX', 'NDEX_PASSWORD', fallback=None)
    return username, password
 
def load_api_key(key_name, config_path=None):
    config = load_config(config_path=config_path)
    # Access the API key
    api_key = config.get('API_KEYS', key_name, fallback=None)
    return api_key

def load_api_keys(config_path=None):
    config = load_config(config_path=config_path)
    # Access the API keys
    openai_api_key = config.get('API_KEYS', 'OPENAI_API_KEY', fallback=None)
    groq_api_key = config.get('API_KEYS', 'GROQ_API_KEY', fallback=None)
    anthropic_api_key = config.get('API_KEYS', 'ANTHROPIC_API_KEY', fallback=None) 
    google_api_key = config.get('API_KEYS', 'GOOGLEAI_KEY', fallback=None)   
    return openai_api_key, groq_api_key, anthropic_api_key, google_api_key

def load_local_server_url(config_path=None):
    config = load_config(config_path=config_path)
    # Access the local server URL
    local_server_url = config.get('API_KEYS', 'LOCAL_MODEL_HOST', fallback=None)
    return local_server_url

# "/Users/idekeradmin/Dropbox/GitHub/agent_kg/src/agent_kg/server.py"  
if __name__ == "__main__":
    config = load_config()
    print(config)


