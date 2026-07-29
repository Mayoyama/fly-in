import pygame


def make_drone_icon(size: int) -> pygame.Surface:
    """Return a size x size Surface (per-pixel alpha) depicting a drone.

    Args:
        size: Width and height of the icon in pixels.

    Returns:
        The drone icon Surface.
    """
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size / 2, size / 2

    body_w, body_h = size * 0.9, size * 0.32
    body_rect = pygame.Rect(0, 0, body_w, body_h)
    body_rect.center = (int(cx), int(cy + size * 0.08))
    pygame.draw.ellipse(surf, (150, 155, 165, 255), body_rect)
    pygame.draw.ellipse(surf, (90, 95, 105, 255), body_rect,
                        max(1, size // 12))

    dome_w, dome_h = size * 0.5, size * 0.4
    dome_rect = pygame.Rect(0, 0, dome_w, dome_h)
    dome_rect.center = (int(cx), int(cy - size * 0.08))
    pygame.draw.ellipse(surf, (80, 210, 235, 230), dome_rect)

    light_r = max(1, int(size * 0.06))
    pygame.draw.circle(surf, (255, 210, 60, 255),
                       (int(cx - body_w * 0.28), int(cy + size * 0.08)),
                       light_r)
    pygame.draw.circle(surf, (255, 210, 60, 255),
                       (int(cx + body_w * 0.28), int(cy + size * 0.08)),
                       light_r)
    return surf


def position_icons(zone_radius: float,
                   count: int) -> list[tuple[float, float]]:
    """Return `count` (x, y) offsets from a zone's center, laid out
    1 2 / 3 4 across the zone's quadrants.

    Args:
        zone_radius: Radius of the zone the icons sit in.
        count: Number of icon offsets to return.

    Returns:
        The list of (x, y) offsets from the zone center.
    """
    quadrant_offsets = [(-1, -1), (1, -1), (-1, 1), (1, 1)]
    inset = zone_radius * 0.55
    positions = []
    for i in range(count):
        qx, qy = quadrant_offsets[i % 4]
        positions.append((qx * inset, qy * inset))
    return positions


def make_overflow_badge(size: int, text: str = "5+") -> pygame.Surface:
    """Return a Surface: white `text`, black outline, transparent bg.

    Args:
        size: Base pixel size driving the font and outline.
        text: The badge text to render.

    Returns:
        The cropped badge Surface.
    """
    surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
    font = pygame.font.SysFont(None, size)
    black = font.render(text, True, (0, 0, 0))
    white = font.render(text, True, (255, 255, 255))
    # Font size scales with height
    center = (surf.get_width() // 2, surf.get_height() // 2)
    # Outline thickness scales with size
    outline_px = max(1, int(size * 0.05))

    for dx in range(-outline_px, outline_px + 1):
        for dy in range(-outline_px, outline_px + 1):
            if dx == 0 and dy == 0:
                continue
            rect = black.get_rect(center=(center[0] + dx, center[1] + dy))
            surf.blit(black, rect)

    rect = white.get_rect(center=center)
    surf.blit(white, rect)

    bound_box = surf.get_bounding_rect()
    bound_box.inflate_ip(4, 4)
    cropped = pygame.Surface(bound_box.size, pygame.SRCALPHA)
    cropped.blit(surf, (0, 0), bound_box)
    return cropped


def get_scaled_img(win_width: int, win_height: int) -> pygame.Surface:
    """Return the terrain background image scaled and cropped to fill
    the window, or a plain dark fallback if the image can't be loaded.

    Args:
        win_width: Target window width in pixels.
        win_height: Target window height in pixels.

    Returns:
        The scaled-and-cropped background Surface.
    """
    try:
        bkg_img = pygame.image.load("resources/terrain_v1.png")
        scale = max((win_width / bkg_img.get_width()),
                    (win_height / bkg_img.get_height()))
        bkg_width = bkg_img.get_width() * scale
        bkg_height = bkg_img.get_height() * scale
        b_surf = pygame.transform.smoothscale(bkg_img, (bkg_width, bkg_height))
        crop_x = int((bkg_width - win_width) / 2)
        crop_y = int((bkg_height - win_height) / 2)
        crop_rect = pygame.Rect(crop_x, crop_y, win_width, win_height)
        scaled_surf = b_surf.subsurface(crop_rect)
    except (FileNotFoundError, IsADirectoryError, PermissionError):
        scaled_surf = pygame.Surface((win_width, win_height))
        scaled_surf.fill((10, 10, 10))
    return scaled_surf
