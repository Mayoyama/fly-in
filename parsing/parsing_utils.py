def convert_atoi(value: str) -> int:
    """Convert a string to an int, re-raising ValueError on failure."""
    try:
        num = int(value)
    except ValueError:
        raise
    return num
