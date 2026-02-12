import time
import logging

# Use a specific logger instead of root logger to avoid duplicate messages
_timing_logger = logging.getLogger("timing_helper")
_timing_logger.propagate = False
if not _timing_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    _timing_logger.addHandler(_handler)
    _timing_logger.setLevel(logging.INFO)

def timed_function(func):
    """
    A decorator to measure and log the execution time of a function.
    """
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        _timing_logger.info(f"Function '{func.__name__}' executed in {elapsed_time:.4f} seconds.")
        return result
    return wrapper

# @timed_function
# def my_sample_function(duration):
#     """
#     A sample function to demonstrate time logging.
#     """
#     logging.info(f"Executing my_sample_function for {duration} seconds...")
#     time.sleep(duration)
#     logging.info("my_sample_function finished.")
#     return "Task Completed"
