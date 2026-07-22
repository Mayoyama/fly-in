from re import match
from typing import Any
from pydantic import BaseModel, Field, ConfigDict
from pydantic import field_validator
from models.zone import HubRole, ZoneType


class ZoneInfo(BaseModel):
    """Validated data for a single zone parsed from a map file."""
    model_config = ConfigDict(extra="forbid")
    zone_name: str = Field(min_length=1)
    x_coord: int
    y_coord: int
    zone: ZoneType = ZoneType.NORMAL
    color: str | None = Field(default=None)
    max_drones: int = Field(ge=1, default=1)

    @field_validator("zone_name")
    @classmethod
    def exclude_chars(cls, value: str) -> str:
        banned = {"-", " "}
        found = banned.intersection(value)
        if found:
            raise ValueError(f"Invalid zone name characters found: "
                             f"{', '.join(found)}")
        return value


class ConnectionInfo(BaseModel):
    """Validated data for a single zone-to-zone connection parsed
    from a map file."""
    model_config = ConfigDict(extra="forbid")
    max_link_capacity: int = Field(ge=1, default=1)
    name1: str = Field(min_length=1)
    name2: str = Field(min_length=1)

    @field_validator("name1", "name2")
    @classmethod
    def exclude_chars(cls, value: str) -> str:
        banned = {"-", " "}
        found = banned.intersection(value)
        if found:
            raise ValueError(f"Invalid zone name characters found: "
                             f"{', '.join(found)}")
        return value


def _convert_atoi(value: str) -> int:
    """Convert a string to an int, re-raising ValueError on failure."""
    try:
        num = int(value)
    except ValueError:
        raise
    return num


def _get_parsing_data(path_to_map_file: str) -> list[str]:
    """Read a map file and return its lines.

    Raises:
        FileNotFoundError, PermissionError, IsADirectoryError,
        NotADirectoryError: If the file can't be opened.
    """
    with open(path_to_map_file, "r") as file_obj:
        map_data = file_obj.readlines()
    return map_data


def _create_zone_info(line: str) -> tuple[HubRole, ZoneInfo]:
    """Parse a single 'hub'/'start_hub'/'end_hub' line into a
    (HubRole, ZoneInfo) pair.

    Raises:
        ValueError: If the line's syntax, hub type, or metadata is invalid.
    """
    line_data = line.split(':', maxsplit=1)
    if len(line_data) != 2:
        raise ValueError("Invalid line syntax, wrong number of ':' detected "
                         "in zone info")
    if line_data[0] == 'hub':
        hub_type = HubRole.REGULAR
    elif line_data[0] == 'start_hub':
        hub_type = HubRole.START
    elif line_data[0] == 'end_hub':
        hub_type = HubRole.END
    else:
        raise ValueError("Invalid hub type")
    zone_data = line_data[1].removeprefix(' ').split('[', maxsplit=1)
    name_xy_regex = r"^([^-\s]+)\s(-?\d+)\s(-?\d+)$"
    zone_match = match(name_xy_regex, zone_data[0].rstrip())
    if not zone_match:
        raise ValueError("Invalid hub information format [name x y]")
    name, x, y = zone_match.groups()
    metadata: dict[str, Any] = {}
    if len(zone_data) == 2:
        if not zone_data[1].rstrip().endswith(']'):
            raise ValueError("Invalid metadata format, missing closing ']'")
        if zone_data[1].strip() == ']':
            raise ValueError(f"Invalid empty metadata field "
                             f"'[{zone_data[1].rstrip()}'")
        metadata_string = zone_data[1].rstrip().removesuffix(']')
        if ']' in metadata_string:
            raise ValueError("Invalid metadata format, misplaced ']'")
        else:
            metadata_kv_regex = r"^(\w+)=([^\]\s]+)$"
            for element in metadata_string.split(' '):
                kv_match = match(metadata_kv_regex, element)
                if not kv_match:
                    raise ValueError("Invalid metadata k:v pair(s)")
                key, value = kv_match.groups()
                if key in metadata:
                    raise ValueError(f"Duplicate metadata key '{key}' "
                                     "detected")
                metadata[key] = value
    zone_info = ZoneInfo(
        zone_name=name,
        x_coord=_convert_atoi(x),
        y_coord=_convert_atoi(y),
        **metadata
    )
    return hub_type, zone_info


def _create_connection_info(line: str) -> ConnectionInfo:
    """Parse a single 'connection:' line into a ConnectionInfo.

    Raises:
        ValueError: If the line's syntax or metadata is invalid.
    """
    line_data = line.split(':', maxsplit=1)
    if len(line_data) != 2:
        raise ValueError("Invalid line syntax, wrong number of ':' detected "
                         "in zone connection info")
    connections = line_data[1].removeprefix(' ').split('[', maxsplit=1)
    metadata: dict[str, Any] = {}
    connex_regex = r"^([^-\s]+)-([^-\s]+)$"
    connex_match = match(connex_regex, connections[0].rstrip())
    if not connex_match:
        raise ValueError("Invalid connection syntax "
                         "'<name1>-<name2> [metadata]'")
    zone1, zone2 = connex_match.groups()
    if len(connections) == 2:
        if not connections[1].rstrip().endswith(']'):
            raise ValueError("Invalid metadata format, missing closing ']'")
        if connections[1].strip() == ']':
            raise ValueError(f"Invalid empty metadata field "
                             f"'[{connections[1].rstrip()}'")
        metadata_string = connections[1].rstrip().removesuffix(']')
        if ']' in metadata_string:
            raise ValueError("Invalid metadata format, misplaced ']'")
        else:
            metadata_kv_regex = r"^(\w+)=([^\]\s]+)$"
            kv_match = match(metadata_kv_regex, metadata_string)
            if not kv_match:
                raise ValueError("Invalid metadata k:v pair(s)")
            key, value = kv_match.groups()
            metadata[key] = value
    conn_info = ConnectionInfo(
        name1=zone1,
        name2=zone2,
        **metadata
    )
    return conn_info


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
                    self.drone_count = _convert_atoi(raw_count)
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
                        hub_type, zone_info = _create_zone_info(line)
                        self.zone_list.append((hub_type, zone_info))
                    elif line.startswith("connection:"):
                        connex = _create_connection_info(line)
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
