from models.zone import HubRole
from .zone_info import ZoneInfo
from .connection_info import ConnectionInfo
from .parsing_utils import convert_atoi


def _get_parsing_data(path_to_map_file: str) -> list[str]:
    """Read a map file and return its lines.

    Raises:
        FileNotFoundError, PermissionError, IsADirectoryError,
        NotADirectoryError: If the file can't be opened.
    """
    with open(path_to_map_file, "r") as file_obj:
        map_data = file_obj.readlines()
    return map_data


class Parser:
    def __init__(self, path_to_map_file: str) -> None:
        """Load raw map file contents for later parsing.

        Args:
            path_to_map_file: Path to the map file to read.

        Raises:
            FileNotFoundError, PermissionError, IsADirectoryError,
            NotADirectoryError: If the file can't be opened.
        """
        self.drone_count = 0
        self.zone_list: list[tuple[HubRole, ZoneInfo]] = []
        self.connection_list: list[ConnectionInfo] = []
        try:
            self.map_data = _get_parsing_data(path_to_map_file)
        except (FileNotFoundError, PermissionError,
                IsADirectoryError, NotADirectoryError):
            raise

    def parse_map_data(self) -> None:
        """Parse the loaded map data into drone_count, zone_list, and
        connection_list.

        Raises:
            ValueError: If the map format is invalid, e.g. missing
                start/end hub, duplicate zone names, duplicate
                connections, or malformed lines (each wrapped with
                the offending line number).
        """
        first_line = True
        has_start = False
        has_end = False
        for i, line in enumerate(self.map_data, start=1):
            if line.startswith('#') or line.strip() == '':
                continue

            if first_line:
                if line.startswith('nb_drones:'):
                    raw_count = line.split(':', maxsplit=1)[1]
                    self.drone_count = convert_atoi(raw_count)
                    if self.drone_count <= 0:
                        raise ValueError(f"Line {i}: [nb_drones] must be a "
                                         "positive integer")
                    first_line = False
                else:
                    raise ValueError(f"Line {i}: [nb_drones] field must be on "
                                     "the first line")
            else:
                try:
                    if line.startswith('nb_drones:'):
                        raise ValueError("[nb_drones] field must be"
                                         " on the first line")
                    elif (
                      line.startswith('start_hub:')
                      or line.startswith('end_hub:')
                      or line.startswith('hub:')
                      ):
                        if line.startswith('start_hub:'):
                            if has_start:
                                raise ValueError("more than one "
                                                 "[start_hub] detected")
                            else:
                                has_start = True
                        if line.startswith('end_hub:'):
                            if has_end:
                                raise ValueError("more than one "
                                                 "[end_hub] detected")
                            else:
                                has_end = True
                        hub_type, zone_info = ZoneInfo.create_zone_info(line)
                        self.zone_list.append((hub_type, zone_info))
                    elif line.startswith("connection:"):
                        connex = ConnectionInfo.create_connection_info(line)
                        zone_names_so_far = {
                            zone_info.zone_name
                            for _, zone_info in self.zone_list
                        }
                        name1_missing = (
                            connex.name1 not in zone_names_so_far)
                        name2_missing = (
                            connex.name2 not in zone_names_so_far)
                        if name1_missing or name2_missing:
                            missing = (connex.name1 if name1_missing
                                       else connex.name2)
                            raise ValueError(
                                "connection references undefined "
                                f"zone '{missing}'"
                            )
                        self.connection_list.append(connex)
                    else:
                        raise ValueError("invalid config line "
                                         f"detected [{line.strip()}]")
                except ValueError as e:
                    raise ValueError(f"Line {i}: {e}") from e

        if not has_end or not has_start:
            missing = ("start_hub" if not has_start else "end_hub")
            raise ValueError(f"Map error: missing required {missing}")

        zones = [zone_info.zone_name for _, zone_info in self.zone_list]
        if len(zones) != len(set(zones)):
            raise ValueError("Map error: duplicate zone names detected")

        namelist: list[frozenset[str]] = []
        for conn_info in self.connection_list:
            namelist.append(frozenset({conn_info.name1, conn_info.name2}))
        if len(namelist) != len(set(namelist)):
            raise ValueError("Map error: duplicate map connections pairs "
                             "detected")
