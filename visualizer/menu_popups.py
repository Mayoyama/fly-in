import pygame
from models.zone import Zone, HubRole
from .color_utils import draw_rainbow_outline
from .icons_images import make_drone_icon, make_overflow_badge


def make_popup(name: str, zone_info: Zone) -> pygame.Surface:
    font = pygame.font.SysFont(None, 16)
    pad = 2

    popup_message = ""
    if zone_info.hub_role == HubRole.START:
        popup_message += f"Name: {name} (START)\n"
    elif zone_info.hub_role == HubRole.END:
        popup_message += f"Name: {name} (END)\n"
    else:
        popup_message += f"Name: {name}\n"
    popup_message += (f"Co-ords: {zone_info.coords}\n"
                      f"Current: {zone_info.curr_drone_count}\n"
                      f"Max: {zone_info.max_drones}")

    lines = popup_message.split("\n")
    line_surfs = [font.render(line, True, "black") for line in lines]

    popup_width = max(line.get_width() for line in line_surfs) + (pad * 2)
    popup_height = sum(line.get_height() for line in line_surfs) + (pad * 2)

    popup_surf = pygame.Surface((popup_width, popup_height))
    popup_surf.fill("white")
    pygame.draw.rect(popup_surf, "royal blue", popup_surf.get_rect(), 1)

    y = pad
    for line_surf in line_surfs:
        rect = line_surf.get_rect(topleft=(pad, y))
        popup_surf.blit(line_surf, rect)
        y += line_surf.get_height()
    return popup_surf

def draw_menu(win_width: int, win_height: int,
              menu_height: int) -> pygame.Surface:
    menu_surf = pygame.Surface((win_width, menu_height))
    menu_surf.fill((0, 128, 128), menu_surf.get_rect())
    menu_font = pygame.font.SysFont(None, 16)
    drone = make_drone_icon(14)
    plus5 = make_overflow_badge(14)
    radius = 7
    gap_internal = 5
    gap_elements = 20

    drone_surf = menu_font.render("Drone", True, "black")
    plus5_surf = menu_font.render("5+ Drones", True, "black")
    prio_surf = menu_font.render("Priority Zone", True, "black")
    restricted_surf = menu_font.render("Restricted Zone", True, "black")
    blocked_surf = menu_font.render("Blocked Zone", True, "black")

    drone_total_w = drone.get_width() + gap_internal + drone_surf.get_width()
    plus5_total_w = plus5.get_width() + gap_internal + plus5_surf.get_width()

    restr_total_w = (radius * 2) + gap_internal + restricted_surf.get_width()
    blocked_total_w = (radius * 2) + gap_internal + blocked_surf.get_width()
    prio_total_w = (radius * 2) + gap_internal + prio_surf.get_width()

    row1_width = drone_total_w + gap_elements + plus5_total_w
    row2_width = (restr_total_w + gap_elements + blocked_total_w
                  + gap_elements + prio_total_w)

    row1_start_x = (win_width // 2) - (row1_width // 2)
    row2_start_x = (win_width // 2) - (row2_width // 2)

    x, y = row1_start_x, 10  
    drone_rect = menu_surf.blit(drone, (x, y))
    x = drone_rect.right + gap_internal       
    drone_label_rect = menu_surf.blit(drone_surf, (x, y + 2))

    x = drone_label_rect.right + 20
    plus5_rect = menu_surf.blit(plus5, (x, y))
    x = plus5_rect.right + gap_internal
    menu_surf.blit(plus5_surf, (x, y + 2))

    x, y = row2_start_x, 32
    center_offset_y = y + radius
    draw_rainbow_outline(menu_surf, (x + radius, center_offset_y), radius, 60)
    x += (radius * 2) + gap_internal
    prio_rect = menu_surf.blit(prio_surf, (x, y + 2))

    x = prio_rect.right + 20
    pygame.draw.circle(menu_surf, (255, 95, 31),
                       (x + radius, center_offset_y), radius, 2)
    x += (radius * 2) + 5
    rest_rect = menu_surf.blit(restricted_surf, (x, y + 2))

    x = rest_rect.right + 20
    pygame.draw.circle(menu_surf, (255, 34, 38),
                       (x + radius, center_offset_y), radius, 2)
    x += (radius * 2) + 5
    menu_surf.blit(blocked_surf, (x, y + 2))

    return menu_surf
