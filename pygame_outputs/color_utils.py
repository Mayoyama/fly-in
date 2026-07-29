from colorsys import hsv_to_rgb
from math import pi, cos, sin
import pygame


def _word_to_color(word: str) -> tuple[int, int, int]:
    """Deterministically derive a brightened RGB color from a string.

    Args:
        word: The string to derive a color from.

    Returns:
        The derived (r, g, b) color.
    """
    def rescale_brightness(value: int) -> int:
        """Scale a 0-255 channel value into a brightened range.

        Args:
            value: The 0-255 channel value to rescale.

        Returns:
            The brightened channel value.
        """
        min_brightness = 15
        return min_brightness + int((value) * (255 - min_brightness) / 255)

    total = sum(ord(c) for c in word)
    r = (total * 37) % 256
    g = (total * 59) % 256
    b = (total * 83) % 256
    return rescale_brightness(r), rescale_brightness(g), rescale_brightness(b)


def resolve_color(name: str | None) -> pygame.Color:
    """Resolve a zone's color name to a pygame Color.

    Falls back to a derived color for unrecognized names, or dark grey
    if name is None.

    Args:
        name: The color name to resolve, or None.

    Returns:
        The resolved pygame Color.
    """
    if name is None:
        return pygame.Color(30, 30, 30)
    try:
        return pygame.Color(name)
    except ValueError:
        return pygame.Color(*_word_to_color(name))


def draw_rainbow_outline(screen: pygame.Surface, center: tuple[int, int],
                         radius: float, segments: int) -> None:
    """Draw a multi-segment rainbow-gradient ring outline at center,
    supersampled for a smooth (anti-aliased) edge.

    Args:
        screen: The surface to draw the outline onto.
        center: The (x, y) pixel center of the ring.
        radius: The ring's radius in pixels.
        segments: Number of colored segments around the ring.
    """
    supersample = 4
    width = int(max(1, 0.3 * radius))
    outline_radius = radius
    margin = width + 2
    diameter = int(2 * (outline_radius + margin))
    hi_res_size = diameter * supersample

    ring_surf = pygame.Surface((hi_res_size, hi_res_size), pygame.SRCALPHA)
    hi_cx = hi_res_size / 2
    hi_cy = hi_res_size / 2
    hi_radius = outline_radius * supersample
    hi_width = width * supersample

    for i in range(segments):
        start_angle = 2 * pi * i / segments
        end_angle = 2 * pi * (i + 1) / segments
        hue = i / segments
        r, g, b = hsv_to_rgb(hue, 1, 1)
        color = (int(r * 255), int(g * 255), int(b * 255))
        pixel_point1 = (hi_cx + hi_radius * cos(start_angle),
                        hi_cy + hi_radius * sin(start_angle))
        pixel_point2 = (hi_cx + hi_radius * cos(end_angle),
                        hi_cy + hi_radius * sin(end_angle))
        pygame.draw.line(ring_surf, color, pixel_point1,
                         pixel_point2, hi_width)

    smooth_surf = pygame.transform.smoothscale(ring_surf, (diameter, diameter))
    dest_rect = smooth_surf.get_rect(center=center)
    screen.blit(smooth_surf, dest_rect)


def draw_rainbow_line(screen: pygame.Surface, start_pt: tuple[int, int],
                      end_pt: tuple[int, int], width: int, segments: int,
                      phase: float = 0.0) -> None:
    """Draw the segment p1->p2 as a flowing rainbow gradient.

    Args:
        screen: The surface to draw onto.
        start_pt: The (x, y) start point in pixels.
        end_pt: The (x, y) end point in pixels.
        width: Line thickness in pixels.
        segments: Number of colored sub-segments along the line.
        phase: Hue offset (advance it over time for a flowing effect).
    """
    x1, y1 = start_pt
    x2, y2 = end_pt
    for i in range(segments):
        t1, t2 = i / segments, (i + 1) / segments
        r, g, b = hsv_to_rgb((t1 + phase) % 1.0, 1, 1)
        color = (int(r * 255), int(g * 255), int(b * 255))
        sx, sy = (x1 + (x2 - x1) * t1), (y1 + (y2 - y1) * t1)
        ex, ey = (x1 + (x2 - x1) * t2), (y1 + (y2 - y1) * t2)
        pygame.draw.line(screen, color, (sx, sy), (ex, ey), width)
