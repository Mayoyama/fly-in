from re import match
from typing import Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from models import HubRole, ZoneType
from .parsing_utils import convert_atoi


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
        """Reject zone names containing dashes or spaces.

        Args:
            value: The zone name to validate.

        Returns:
            The validated zone name, unchanged.

        Raises:
            ValueError: If the name contains a dash or space.
        """
        banned = {"-", " "}
        found = banned.intersection(value)
        if found:
            raise ValueError(f"Invalid zone name characters found: "
                             f"{', '.join(found)}")
        return value

    @classmethod
    def create_zone_info(cls, line: str) -> tuple[HubRole, "ZoneInfo"]:
        """Parse a single 'hub'/'start_hub'/'end_hub' line into a
        (HubRole, ZoneInfo) pair.

        Args:
            line: The raw zone definition line to parse.

        Returns:
            The parsed (HubRole, ZoneInfo) pair.

        Raises:
            ValueError: If the line's syntax, hub type, or metadata is invalid.
        """
        line_data = line.split(':', maxsplit=1)
        if len(line_data) != 2:
            raise ValueError("Invalid line syntax, wrong number of ':' "
                             "detected in zone info")
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
                raise ValueError("Invalid metadata format, missing "
                                 "closing ']'")
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
            x_coord=convert_atoi(x),
            y_coord=convert_atoi(y),
            **metadata
        )
        if hub_type in (HubRole.START, HubRole.END) and \
                zone_info.zone == ZoneType.BLOCKED:
            raise ValueError("start_hub/end_hub cannot be a blocked zone")
        return hub_type, zone_info
