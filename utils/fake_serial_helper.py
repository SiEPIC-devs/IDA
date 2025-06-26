import time
from threading import Lock

class FakeSerial:
    """
    A minimal stand‐in for serial.Serial that “echoes back” plausible MMC100 responses. This is just from ChatGPT, 
    so I have no idea how it works. Intended for high level testing
    """
    def __init__(self, *args, **kwargs):
        # We ignore real port, baud, timeout, etc.
        self._lock = Lock()
        self._last_cmd = b""

    def write(self, data: bytes):
        # Store the last command (so that read_until() knows what to reply).
        with self._lock:
            self._last_cmd = data
        # Simulate a tiny transfer delay
        time.sleep(0.001)

    def read_until(self, terminator: bytes = b"\r\n") -> bytes:
        # Wait a tiny bit to simulate response time
        time.sleep(0.002)

        with self._lock:
            data = self._last_cmd.decode("ascii", errors="ignore").strip()

        # If command was “nSTA?”, return “8” (meaning bit‐3=1 → stopped).
        if data.endswith("STA?"):
            return b"8\r\n"

        # If command was “nPOS?”, return “0.000000,0”
        if data.endswith("POS?"):
            # The “0” after the comma is the “mode” byte; we ignore it.
            return b"0.000000,0\r\n"

        # For any other command (FBK3, ZRO, MVR…, MLN, MLP, etc.), we return a
        # generic “OK” or no‐payload. MMC100 often doesn’t echo on write; read_until
        # here just blocks until terminator, so we return an empty line:
        return b"\r\n"

    def close(self):
        pass

    @property
    def is_open(self):
        return True

    def open(self):
        pass
