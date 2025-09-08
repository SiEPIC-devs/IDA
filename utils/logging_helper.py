import logging

def setup_logger(name,dev=None, debug_mode=False):
      logger = logging.getLogger(name)
      level = logging.DEBUG if debug_mode else logging.INFO

      handler = logging.StreamHandler()
      handler.setLevel(level)
      formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
      handler.setFormatter(formatter)

      logger.setLevel(level)
      logger.addHandler(handler)
      return logger