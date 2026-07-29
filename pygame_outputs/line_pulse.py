from .color_utils import resolve_color
from math import sin, pi
import pygame


def draw_pulsing_line(screen: pygame.Surface, start_pt: tuple[float, float],
                      end_pt: tuple[float, float], width: int = 2,
                      min_alpha: float = 0.2, max_alpha: float = 1.0,
                      frequency: float = 0.5, color: str = "green") -> None:
    """Draw a pulsing line between two points, smoothly fading opacity
    between min_alpha and max_alpha over time.

    Args:
        screen: The surface to draw onto.
        start_pt: The (x, y) start point in pixels.
        end_pt: The (x, y) end point in pixels.
        width: Line thickness in pixels.
        min_alpha: Lowest opacity in the pulse cycle (0.0-1.0).
        max_alpha: Highest opacity in the pulse cycle (0.0-1.0).
        frequency: Pulse cycles per second.
        color: Name of the line's color, resolved via resolve_color.
    """
    if frequency <= 0:
        raise ValueError("Frequency must be a positive non-zero value")
    phase = pygame.time.get_ticks() / 1000.0
    intensity = (min_alpha + ((max_alpha - min_alpha) / 2)
                 * (sin(2 * pi * frequency * phase) + 1))
    alpha = int(intensity * 255)
    x1, y1 = start_pt
    x2, y2 = end_pt
    padding = width * 5
    origin_x, origin_y = min(x1, x2) - padding, min(y1, y2) - padding

    pulse_color = resolve_color(color)
    surf_size = abs(x2 - x1) + padding * 2, abs(y2 - y1) + padding * 2
    pulse_surf = pygame.Surface(surf_size, pygame.SRCALPHA)
    surf_start_pt = (x1 - origin_x, y1 - origin_y)
    surf_end_pt = (x2 - origin_x, y2 - origin_y)
    pygame.draw.line(pulse_surf, pulse_color, surf_start_pt,
                     surf_end_pt, width)

    pulse_surf.set_alpha(alpha)
    bounding_box = pulse_surf.get_bounding_rect()

    bounding_box.inflate_ip(4, 4)
    cropped = pygame.Surface(bounding_box.size, pygame.SRCALPHA)
    cropped.blit(pulse_surf, (0, 0), bounding_box)

    screen.blit(cropped, (origin_x + bounding_box.left,
                          origin_y + bounding_box.top))
