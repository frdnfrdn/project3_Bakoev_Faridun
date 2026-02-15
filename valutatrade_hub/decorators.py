"""Decorators for cross-cutting concerns: logging, timing, confirmation."""

import functools
import logging
import time


def log_action(func):
    """Decorator that logs function calls, results, and execution time.

    Logs at INFO level on success, ERROR level on failure.
    """
    logger = logging.getLogger(func.__module__)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Wrap the function with logging."""
        func_name = func.__name__
        logger.info("Calling %s", func_name)
        start = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            logger.info("%s completed in %.3fs", func_name, elapsed)
            return result
        except Exception as exc:
            elapsed = time.time() - start
            logger.error(
                "%s failed after %.3fs: %s: %s",
                func_name,
                elapsed,
                type(exc).__name__,
                exc,
            )
            raise

    return wrapper


def confirm_action(message: str = "Are you sure?"):
    """Decorator that asks for user confirmation before executing.

    Args:
        message: Confirmation prompt to display.
    """

    def decorator(func):
        """Create the decorator with the given message."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """Ask for confirmation, then call the function."""
            answer = input(f"{message} (y/n): ").strip().lower()
            if answer in ("y", "yes"):
                return func(*args, **kwargs)
            print("Action cancelled.")
            return None

        return wrapper

    return decorator


def log_time(func):
    """Decorator that prints the execution time of a function."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Measure and print execution time."""
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"[{func.__name__}] executed in {elapsed:.3f}s")
        return result

    return wrapper
