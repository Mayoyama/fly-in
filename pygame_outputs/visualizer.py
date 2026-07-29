import pygame
from models import ZoneConnection, Zone, ZoneType
from .layout import Dimensions, Layout
from .color_utils import resolve_color, draw_rainbow_outline
from .line_pulse import draw_pulsing_line
from .icons_images import (make_drone_icon, make_overflow_badge,
                           position_icons, get_scaled_img)
from .menu_popups import (make_zone_popup, draw_menu, draw_heading,
                          make_link_popup)


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
        self.layout = Layout(self.zones, self.win_width, self.win_height,
                             self.dimensions)
        self.background_img = get_scaled_img(self.win_width, self.win_height)

        self.screen = pygame.display.set_mode((self.win_width,
                                               self.win_height))
        self.clock = pygame.time.Clock()
        self.running = True

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
            max(6, int(0.8 * self.layout.zone_radius)))
        # Includes badge size calculation
        self.overflow_badge = make_overflow_badge(
            max(8, int(0.9 * self.layout.zone_radius)))
        self.positions = {name: self.layout.zone_to_pixel(zone_info.coords)
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

        mouse_pos = pygame.mouse.get_pos()
        hover_zone = self.layout.zone_at(mouse_pos, self.positions)
        hover_link = (None if hover_zone else
                      self.layout.connection_at(mouse_pos, self.positions,
                                                self.connections))

        self.screen.blit(self.background_img, (0, 0))
        self.screen.blit(self.heading_surface, (0, 0))
        self.screen.blit(self.menu_surface,
                         (0, self.win_height - self.dimensions.menu_height))
        for key, connection in self.connections.items():
            p1 = self.positions[connection.z1_name]
            p2 = self.positions[connection.z2_name]
            if key == hover_link:
                # draw_rainbow_line(self.screen, p1, p2, 4, 30, True, 1500)
                draw_pulsing_line(self.screen, p1, p2, color="gold",
                                  frequency=1.0)
            else:
                pygame.draw.line(self.screen, (175, 175, 175), p1, p2, 2)

        for name, zone in self.zones.items():
            color = resolve_color(zone.color)
            pos = self.positions[name]
            pygame.draw.circle(self.screen, color, pos,
                               self.layout.zone_radius)

            if zone.zone_type == ZoneType.BLOCKED:
                pygame.draw.circle(self.screen, (255, 34, 38),
                                   pos, self.layout.zone_radius, 3)
            elif zone.zone_type == ZoneType.RESTRICTED:
                pygame.draw.circle(self.screen, (255, 95, 31),
                                   pos, self.layout.zone_radius, 3)
            elif zone.zone_type == ZoneType.PRIORITY:
                draw_rainbow_outline(self.screen, pos,
                                     self.layout.zone_radius, 120)
            count = zone.curr_drone_count
            shown = min(count, 4)
            if shown > 0:
                pos_icons = position_icons(self.layout.zone_radius, shown)
                for offset in pos_icons:
                    rect = self.drone_icon.get_rect(
                        center=(pos[0] + offset[0], pos[1] + offset[1]))
                    self.screen.blit(self.drone_icon, rect)
                if count >= 5:
                    rect = self.overflow_badge.get_rect(center=pos)
                    self.screen.blit(self.overflow_badge, rect)
        self._render_popup(mouse_pos, hover_zone, hover_link)
        if moving_positions is not None:
            for position in moving_positions:
                rect = self.drone_icon.get_rect(center=position)
                self.screen.blit(self.drone_icon, rect)
        pygame.display.flip()

    def _render_popup(self, mouse_pos: tuple[int, int],
                      hover_zone: str | None,
                      hover_link: frozenset[str] | None) -> None:
        """Draw the info popup for the hovered zone, or connection if no
        zone is under the cursor and cursor is near a connection line.

        Args:
            mouse_pos: Current (x, y) cursor position.
            hover_zone: Name of the hovered zone, or None.
            hover_link: Key of the hovered connection, or None.
        """
        win_bounds = pygame.Rect(0, 0, self.win_width,
                                 self.win_height - self.dimensions.menu_height)

        if hover_zone:
            x, y = self.positions[hover_zone]
            popup_surface = make_zone_popup(self.zones[hover_zone])
            popup_rect = popup_surface.get_rect()
            popup_rect.midtop = x, int(y + self.layout.zone_radius + 2)
            popup_rect.clamp_ip(win_bounds)
            self.screen.blit(popup_surface, popup_rect)

        elif hover_link:
            conn = self.connections[hover_link]
            popup_surface = make_link_popup(conn, self.zones[conn.z1_name],
                                            self.zones[conn.z2_name])
            popup_rect = popup_surface.get_rect()
            popup_rect.midtop = mouse_pos[0], mouse_pos[1] + 12
            popup_rect.clamp_ip(win_bounds)
            self.screen.blit(popup_surface, popup_rect)
