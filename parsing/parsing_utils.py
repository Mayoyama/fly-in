def convert_atoi(value: str) -> int:
    """Convert a string to an int, re-raising ValueError on failure.

    Args:
        value: The string to convert.

    Returns:
        The parsed integer.

    Raises:
        ValueError: If the string is not a valid integer.
    """
    try:
        num = int(value)
    except ValueError:
        raise
    return num
