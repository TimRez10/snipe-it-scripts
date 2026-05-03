import logging
import logging.config
import json

def setup_logger(log_conf_file: str="log_config.json", logger_name: str="basicLogger") -> logging.Logger:
    """Set up and return a logger based on a JSON configuration file."""
    with open(log_conf_file, 'r') as f:
        log_config = json.load(f)
        logging.config.dictConfig(log_config)
    return logging.getLogger(logger_name)


def get_logger(logger_name: str="basicLogger") -> logging.Logger:
    """Get a logger by name."""
    return logging.getLogger(logger_name)