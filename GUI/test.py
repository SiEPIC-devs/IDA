from NIR.nir_manager import NIRManager
from NIR.config.nir_config import NIRConfiguration

if __name__ == "__main__":
    config = NIRConfiguration()
    a = NIRManager(config)
    a.initialize()