from dataclasses import dataclass
from models import Zone, ZoneConnection
from math import sqrt


@dataclass(frozen=True)
class Dimensions:
    """Fixed pixel sizes for the screen's padding, heading, and menu bar."""
    padding: int = 40
    heading_height: int = 40
    menu_height: int = 55


class Layout:
    def __init__(self, zones: dict[str, Zone], win_width: int,
                 win_height: int, dimensions: Dimensions) -> None:
        """Compute the pixel geometry used to render a map's zones.

        Args:
            zones: Map of zone name to Zone, used to derive bounds.
            win_width: Window width in pixels.
            win_height: Window height in pixels.
            dimensions: Fixed padding/heading/menu sizes.
        """
        self.win_width = win_width
        self.win_height = win_height
        self.dimensions = dimensions
        self.min_x, self.min_y, self.max_x, self.max_y = \
            self._calc_minmax_xy(zones)
        diff_x = self.max_x - self.min_x
        diff_y = self.max_y - self.min_y
        self.scale = self._calc_scale(diff_x, diff_y)
        self.extra_x, self.extra_y = self._calc_screen_offsets(diff_x, diff_y)
        self.zone_radius = self._calc_radius()

    @staticmethod
    def _calc_minmax_xy(zones: dict[str, Zone]) -> tuple[int, int, int, int]:
        """Return the (min_x, min_y, max_x, max_y) bounds of all zone
        coords.

        Args:
            zones: Map of zone name to Zone to derive bounds from.

        Returns:
            The (min_x, min_y, max_x, max_y) coordinate bounds.
        """
        min_x = min(zone.coords[0] for zone in zones.values())
        min_y = min(zone.coords[1] for zone in zones.values())
        max_x = max(zone.coords[0] for zone in zones.values())
        max_y = max(zone.coords[1] for zone in zones.values())

        return min_x, min_y, max_x, max_y

    def _calc_scale(self, diff_x: int, diff_y: int) -> float:
        """Return the pixels-per-map-unit scale factor that fits all zones
        within the available drawing area, preserving aspect ratio.

        Args:
            diff_x: Span of the zones along the x axis.
            diff_y: Span of the zones along the y axis.

        Returns:
            The pixels-per-map-unit scale factor.
        """
        available_width = self.win_width - (self.dimensions.padding * 2)
        available_height = (self.win_height - (self.dimensions.padding * 2)
                            - self.dimensions.heading_height
                            - self.dimensions.menu_height)
        if diff_x == 0 and diff_y == 0:
            return 20
        elif diff_x == 0:
            return available_height / diff_y
        elif diff_y == 0:
            return available_width / diff_x

        x_ratio = available_width / diff_x
        y_ratio = available_height / diff_y
        return min(x_ratio, y_ratio)

    def _calc_screen_offsets(self, diff_x: int, diff_y: int) -> tuple[float,
                                                                      float]:
        """Return (x, y) pixel offsets to center scaled zone coordinates
        within the available drawing area.

        Args:
            diff_x: Span of the zones along the x axis.
            diff_y: Span of the zones along the y axis.

        Returns:
            The (x, y) centering offsets in pixels.
        """
        available_width = self.win_width - (self.dimensions.padding * 2)
        available_height = (self.win_height - (self.dimensions.padding * 2)
                            - self.dimensions.heading_height
                            - self.dimensions.menu_height)
        offset_x = (available_width - diff_x * self.scale) / 2
        offset_y = (available_height - diff_y * self.scale) / 2
        return offset_x, offset_y

    def _calc_radius(self) -> float:
        """Return the pixel radius to draw each zone circle at.

        Returns:
            The zone circle radius in pixels.
        """
        return min(self.scale * 0.4, self.dimensions.padding * 0.9)

    def zone_to_pixel(self, coords: tuple[int, int]) -> tuple[int, int]:
        """Convert a zone's map coordinates to screen pixel coordinates.

        Args:
            coords: The zone's (x, y) map coordinates.

        Returns:
            The (x, y) pixel position on screen.
        """
        x_coord, y_coord = coords
        px = ((x_coord - self.min_x) * self.scale + self.dimensions.padding
              + self.extra_x)
        py = (self.win_height - self.dimensions.padding
              - self.dimensions.menu_height - ((y_coord - self.min_y)
                                               * self.scale + self.extra_y))
        return int(px), int(py)

    def zone_at(self, mouse_pos: tuple[int, int],
                positions: dict[str, tuple[int, int]]) -> str | None:
        """Return the name of the zone under the given pixel position, if any.

        Args:
            mouse_pos: (x, y) pixel coordinates to test.
            positions: Mapping of zone name to its pixel center.

        Returns:
            The zone name if the position falls within its circle, else None.
        """
        mx, my = mouse_pos
        for name, center in positions.items():
            cx, cy = center
            d = sqrt((mx - cx)**2 + (my - cy)**2)
            if d <= self.zone_radius:
                return name
        return None

    def connection_at(self, mouse_pos: tuple[int, int],
                      positions: dict[str, tuple[int, int]],
                      connections: dict[frozenset[str], ZoneConnection]
                      ) -> frozenset[str] | None:
        """Return the name of the connection under the given pixel position,
        if any.

        Args:
            mouse_pos: (x, y) pixel coordinates to test.
            positions: Mapping of zone name to its pixel center.
            connections: Dictionary of zone connections.

        Returns:
            The frozenset of the connection if the position falls within the
            bounds of the line, else None.
        """
        mx, my = mouse_pos
        nearest_key: frozenset[str] | None = None
        px_threshold: float = 4.0
        for key, conn in connections.items():
            x1, y1 = positions[conn.z1_name]
            x2, y2 = positions[conn.z2_name]
            dx, dy = x2 - x1, y2 - y1
            segment = dx * dx + dy * dy
            if segment == 0:
                t: float = 0.0
            else:
                t = max(0.0, min(1.0, (
                    (mx - x1) * dx + (my - y1) * dy) / segment))
            px, py = x1 + t * dx, y1 + t * dy
            dist = ((mx - px) ** 2 + (my - py) ** 2) ** 0.5
            if dist < px_threshold:
                px_threshold, nearest_key = dist, key
        return nearest_key
