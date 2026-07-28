import pygame
from models.connection import ZoneConnection
from models.zone import Zone, ZoneType
from .layout import (Dimensions, calc_minmax_xy, calc_scale,
                     calc_screen_offsets, calc_radius, get_zone_at)
from .color_utils import resolve_color, draw_rainbow_outline
from .icons_images import (make_drone_icon, make_overflow_badge,
                           position_icons, get_scaled_img)
from .menu_popups import make_popup, draw_menu, draw_heading


class Visualizer:
    def __init__(self, zones: dict[str, Zone],
                 connections: dict[frozenset[str], ZoneConnection]) -> None:
        """Set up the pygame window, layout, and static assets.

        Args:
            zones: Map of zone name to Zone, used to compute layout.
            connections: Map of zone-name-pair to ZoneConnection.
        """
        pygame.init()
        pygame.display.set_caption("Fly-in")
        display_info = pygame.display.Info()
        self.zones = zones
        self.connections = connections
        self.dimensions = Dimensions()
        self.win_height = int(display_info.current_h * 0.7)
        self.win_width = int(display_info.current_w * 0.7)
        self.background_img = get_scaled_img(self.win_width, self.win_height)

        self.screen = pygame.display.set_mode((self.win_width,
                                               self.win_height))
        self.clock = pygame.time.Clock()
        self.running = True

        self.min_x, self.min_y, self.max_x, self.max_y = calc_minmax_xy(
            self.zones)
        self.scale = calc_scale(self.win_height, self.win_width,
                                self.dimensions, self.max_x - self.min_x,
                                self.max_y - self.min_y)
        self.extra_x, self.extra_y = \
            calc_screen_offsets(self.win_height,
                                self.win_width, self.dimensions,
                                self.max_x - self.min_x,
                                self.max_y - self.min_y, self.scale)
        self.zone_radius = calc_radius(self.scale, self.dimensions.padding)
        heading_font = "resources/MeaCulpa-Regular.ttf"
        heading_text = "Fly-in: Drone Simulator"
        self.heading_surface = draw_heading(self.win_width,
                                            self.dimensions.heading_height,
                                            heading_text, font_size=25,
                                            font_path=heading_font)
        self.menu_surface = draw_menu(self.win_width, self.win_height,
                                      self.dimensions.menu_height)
        # Includes icon size calculation
        self.drone_icon = make_drone_icon(
            max(6, int(0.8 * self.zone_radius)))
        # Includes badge size calculation
        self.overflow_badge = make_overflow_badge(
            max(8, int(0.9 * self.zone_radius)))
        self.positions = {name: self._zone_to_pixel(zone_info.coords)
                          for name, zone_info in self.zones.items()}

    def wait_to_start(self) -> None:
        """Render the frame with a 'press SPACE to start' overlay and
        block until the user presses SPACE (or closes the window)."""
        self.render_frame()
        font_path = "resources/AlmendraDisplay-Regular.ttf"
        try:
            wait_font = pygame.font.Font(font_path, 50)
        except (FileNotFoundError, IsADirectoryError, PermissionError):
            wait_font = pygame.font.SysFont(None, 60)
        wait_str = "Press SPACE to start simulation"
        wait_surf = wait_font.render(wait_str, True, "black", "white")
        wait_rect = wait_surf.get_rect(center=(self.win_width / 2,
                                               self.win_height / 2))
        self.screen.blit(wait_surf, wait_rect)
        pygame.display.flip()
        while True:
            self.clock.tick(30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                elif (
                  event.type == pygame.KEYDOWN
                  and event.key == pygame.K_SPACE):
                    return

    def _zone_to_pixel(self, coords: tuple[int, int]) -> tuple[int, int]:
        """Convert a zone's map coordinates to screen pixel coordinates."""
        x_coord, y_coord = coords
        px = ((x_coord - self.min_x) * self.scale + self.dimensions.padding
              + self.extra_x)
        py = (self.win_height - self.dimensions.padding
              - self.dimensions.menu_height - ((y_coord - self.min_y)
                                               * self.scale + self.extra_y))
        return int(px), int(py)

    def render_frame(
        self, moving_positions: list[tuple[float, float]] | None = None
    ) -> None:
        """Draw one full frame: background, heading, menu, connections,
        zones, drone icons, and the hover popup, then flip the display.

        Args:
            moving_positions: Optional pixel positions of drones
                currently mid-animation; each gets an extra drone icon
                drawn there on top of the settled zone counts.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
        self.screen.blit(self.background_img, (0, 0))
        self.screen.blit(self.heading_surface, (0, 0))
        self.screen.blit(self.menu_surface,
                         (0, self.win_height - self.dimensions.menu_height))
        for connection in self.connections.values():
            pygame.draw.line(self.screen, (175, 175, 175),
                             self.positions[connection.z1_name],
                             self.positions[connection.z2_name], 2)
        for name, zone in self.zones.items():
            color = resolve_color(zone.color)
            pos = self.positions[name]
            pygame.draw.circle(self.screen, color, pos, self.zone_radius)

            if zone.zone_type == ZoneType.BLOCKED:
                pygame.draw.circle(self.screen, (255, 34, 38),
                                   pos, self.zone_radius, 3)
            elif zone.zone_type == ZoneType.RESTRICTED:
                pygame.draw.circle(self.screen, (255, 95, 31),
                                   pos, self.zone_radius, 3)
            elif zone.zone_type == ZoneType.PRIORITY:
                draw_rainbow_outline(self.screen, pos,
                                     self.zone_radius, 120)
            count = zone.curr_drone_count
            shown = min(count, 4)
            if shown > 0:
                pos_icons = position_icons(self.zone_radius, shown)
                for offset in pos_icons:
                    rect = self.drone_icon.get_rect(
                        center=(pos[0] + offset[0], pos[1] + offset[1]))
                    self.screen.blit(self.drone_icon, rect)
                if count >= 5:
                    rect = self.overflow_badge.get_rect(center=pos)
                    self.screen.blit(self.overflow_badge, rect)
        self._render_popup()
        if moving_positions is not None:
            for position in moving_positions:
                rect = self.drone_icon.get_rect(center=position)
                self.screen.blit(self.drone_icon, rect)
        pygame.display.flip()

    def _render_popup(self) -> None:
        """Draw info popup for whichever zone the mouse is hovering over."""
        win_bounds = pygame.Rect(0, 0, self.win_width,
                                 self.win_height - self.dimensions.menu_height)
        mouse_pos = pygame.mouse.get_pos()
        zone = get_zone_at(mouse_pos, self.positions, self.zone_radius)
        if zone:
            x, y = self.positions[zone]
            popup_surface = make_popup(self.zones[zone])
            popup_rect = popup_surface.get_rect()
            popup_rect.midtop = x, int(y + self.zone_radius + 2)
            popup_rect.clamp_ip(win_bounds)
            self.screen.blit(popup_surface, popup_rect)
