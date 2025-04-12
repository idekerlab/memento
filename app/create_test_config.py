#!/usr/bin/env python3
"""
Create a test configuration file for Memento

This script creates a minimal config.ini file for testing the Memento MCP server.
"""

import os
import configparser
import pathlib

def create_test_config():
    # Create config directory if it doesn't exist
    config_dir = os.path.expanduser('~/memento_config')
    os.makedirs(config_dir, exist_ok=True)
    
    # Create config file
    config_path = os.path.join(config_dir, 'config.ini')
    
    # Check if config already exists
    if os.path.exists(config_path):
        print(f"Config file already exists at {config_path}")
        return config_path
    
    # Create a ConfigParser object
    config = configparser.ConfigParser()
    
    # Add sections and settings
    config['API_KEYS'] = {
        'ANTHROPIC_API_KEY': 'YOUR_ANTHROPIC_API_KEY',
        'OPENAI_API_KEY': 'YOUR_OPENAI_API_KEY',
        'GROQ_API_KEY': 'YOUR_GROQ_API_KEY',
        'GOOGLEAI_KEY': 'YOUR_GOOGLEAI_KEY',
        'LOCAL_MODEL_HOST': 'http://localhost:8000'
    }
    
    config['NDEX'] = {
        'NDEX_USERNAME': 'YOUR_NDEX_USERNAME',
        'NDEX_PASSWORD': 'YOUR_NDEX_PASSWORD'
    }
    
    # Write to file
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    
    print(f"Created test config at {config_path}")
    return config_path

if __name__ == "__main__":
    config_path = create_test_config()
    print(f"Config file location: {config_path}")
    print("Please update the placeholders with your actual API keys and credentials.")
