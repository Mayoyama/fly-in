from colorsys import hsv_to_rgb
from math import pi, cos, sin
import pygame


def word_to_color(word: str) -> tuple[int, int, int]:
    def rescale_brightness(value: int) -> int:
        min_brightness = 30
        return min_brightness + int((value) * (255 - min_brightness) / 255)

    total = sum(ord(c) for c in word)
    r = (total * 37) % 256
    g = (total * 59) % 256
    b = (total * 83) % 256
    return rescale_brightness(r), rescale_brightness(g), rescale_brightness(b)


def resolve_color(name: str | None) -> pygame.Color:
    if name is None:
        return pygame.Color(30, 30, 30)
    try:
        return pygame.Color(name)
    except ValueError:
        return pygame.Color(*word_to_color(name))


def draw_rainbow_outline(screen: pygame.Surface, center: tuple[int, int],
                         radius: float, segments: int) -> None:
    cx, cy = center
    width = int(max(1, 0.3 * radius))
    outline_radius = radius - width / 2
    for i in range(segments):
        start_angle = 2 * pi * i / segments
        end_angle = 2 * pi * (i + 1) / segments
        hue = i / segments
        r, g, b = hsv_to_rgb(hue, 1, 1)
        color = (int(r * 255), int(g * 255), int(b * 255))
        pixel_point1 = (cx + outline_radius * cos(start_angle),
                        cy + outline_radius * sin(start_angle))
        pixel_point2 = (cx + outline_radius * cos(end_angle),
                        cy + outline_radius * sin(end_angle))
        pygame.draw.line(screen, color, pixel_point1, pixel_point2, width)
