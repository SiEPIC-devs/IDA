import logging

# Track which loggers have been configured to prevent duplicate handlers
_configured_loggers = set()


def setup_logger(name, dev=None, debug_mode=False):
    """
    Setup a logger with the given name.
    
    Prevents duplicate handlers by:
    1. Tracking already configured loggers
    2. Setting propagate=False to prevent messages going to root logger
    """
    logger = logging.getLogger(name)
    level = logging.DEBUG if debug_mode else logging.INFO
    logger.setLevel(level)
    
    # Only add handler once per logger name
    if name not in _configured_loggers:
        # Clear any existing handlers first
        logger.handlers.clear()
        
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter('%(name)-15s %(levelname)-8s  %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        _configured_loggers.add(name)
    else:
        # Update existing handler levels if debug_mode changed
        for handler in logger.handlers:
            handler.setLevel(level)
    
    # CRITICAL: Prevent propagation to root logger to avoid duplicate messages
    logger.propagate = False
    
    return logger