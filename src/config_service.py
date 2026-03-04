import yaml
from pathlib import Path

def load_business_config():
    """Load business configuration from YAML file."""
    config_path = Path("config/business.yaml")
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    if config is None:
        raise ValueError("Configuration file is empty")
    
    return config

# Cache the config
_config = None

def get_config():
    """Get cached business configuration."""
    global _config
    if _config is None:
        _config = load_business_config()
    return _config
