from colorsys import hsv_to_rgb
from math import sqrt


def rainbow_text(text: str) -> str:
    """Wrap each character of text in a distinct rainbow-gradient
    color, using ANSI TrueColor escape codes.

    Args:
        text: The text to colorize.

    Returns:
        The text with per-character ANSI color escapes.
    """
    result = ""
    for i, char in enumerate(text):
        hue = i / len(text)
        r, g, b = hsv_to_rgb(hue, 1, 1)
        true_r, true_g, true_b = (int(r * 255), int(g * 255), int(b * 255))
        truecolor_char = f"\033[38;2;{true_r};{true_g};{true_b}m{char}\033[0m"
        result += truecolor_char
    return result


def seeded_color_text(text: str, seed_nb: int) -> str:
    """Color text a deterministic random hue derived from seed_nb, so
    the same seed (e.g. a drone's id) always produces the same color.

    Args:
        text: The text to colorize.
        seed_nb: Seed determining the hue.

    Returns:
        The text wrapped in the seeded ANSI color escape.
    """
    golden_ratio = (sqrt(5) - 1) / 2
    hue = (seed_nb * golden_ratio) % 1.0
    r, g, b = hsv_to_rgb(hue, 1, 1)
    true_r, true_g, true_b = (int(r * 255), int(g * 255), int(b * 255))
    return f"\033[38;2;{true_r};{true_g};{true_b}m{text}\033[0m"
