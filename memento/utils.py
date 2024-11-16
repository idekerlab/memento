# cxdb/utils.py

import configparser
import os

def load_config(section, key, fallback=None, config_path='~/cxdb/config.ini'):
    """
    Load a configuration value from the config file.
    
    Args:
    section (str): The section in the config file.
    key (str): The key for the config value.
    fallback (Any, optional): The fallback value if the key is not found. Defaults to None.
    config_path (str, optional): Path to the config file. Defaults to '~/cxdb/config.ini'.
    
    Returns:
    The value from the config file, or the fallback value if not found.
    """
    config = configparser.ConfigParser()
    expanded_config_file_path = os.path.expanduser(config_path)
    
    # Check if the config file exists
    if not os.path.exists(expanded_config_file_path):
        raise FileNotFoundError(f"Config file not found at {expanded_config_file_path}")
    
    # Read the configuration file
    config.read(expanded_config_file_path)
    
    # Make section and key case-insensitive
    section = section.lower()
    key = key.lower()
    
    # Access the config value
    for config_section in config.sections():
        if config_section.lower() == section:
            for config_key, value in config[config_section].items():
                if config_key.lower() == key:
                    return value
    
    if fallback is not None:
        return fallback
    
    raise ValueError(f"Key '{key}' not found in section '{section}' of the config file")