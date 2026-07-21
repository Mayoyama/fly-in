from dataclasses import dataclass
from models.zone import Zone
from math import sqrt


@dataclass(frozen=True)
class Dimensions:
    padding: int = 20
    heading_height: int = 0
    menu_height: int = 55


def calc_minmax_xy(zones: dict[str, Zone]) -> tuple[int, int, int, int]:
    min_x = min(zone.coords[0] for zone in zones.values())
    min_y = min(zone.coords[1] for zone in zones.values())
    max_x = max(zone.coords[0] for zone in zones.values())
    max_y = max(zone.coords[1] for zone in zones.values())

    return min_x, min_y, max_x, max_y


def calc_scale(win_h: float, win_w: float, dim: Dimensions, diff_x: int,
               diff_y: int) -> float:
    available_width = win_w - (dim.padding * 2)
    available_height = (win_h - (dim.padding * 2) - dim.heading_height
                        - dim.menu_height)
    if diff_x == 0 and diff_y == 0:
        return 20
    elif diff_x == 0:
        return available_height / diff_y
    elif diff_y == 0:
        return available_width / diff_x

    x_ratio = available_width / diff_x
    y_ratio = available_height / diff_y
    return min(x_ratio, y_ratio)


def calc_screen_offsets(win_h: float, win_w: float, dim: Dimensions,
                        diff_x: int, diff_y: int,
                        scale: float) -> tuple[float, float]:
    available_width = win_w - (dim.padding * 2)
    available_height = (win_h - (dim.padding * 2) - dim.heading_height
                        - dim.menu_height)
    offset_x = (available_width - diff_x * scale) / 2
    offset_y = (available_height - diff_y * scale) / 2
    return offset_x, offset_y


def calc_radius(scale: float, padding: int) -> float:
    return min(scale * 0.4, padding * 0.9)


def get_zone_at(mouse_pos: tuple[int, int],
                positions: dict[str, tuple[int, int]],
                rad: float) -> str | None:
    mx, my = mouse_pos
    for name, center in positions.items():
        cx, cy = center
        d = sqrt((mx - cx)**2 + (my - cy)**2)
        if d <= rad:
            return name
    return None
