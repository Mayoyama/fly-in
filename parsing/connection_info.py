from re import match
from typing import Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


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
        """Reject connection endpoint names containing dashes or spaces.

        Args:
            value: The endpoint name to validate.

        Returns:
            The validated endpoint name, unchanged.

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
    def create_connection_info(cls, line: str) -> "ConnectionInfo":
        """Parse a single 'connection:' line into a ConnectionInfo.

        Args:
            line: The raw connection definition line to parse.

        Returns:
            The parsed ConnectionInfo.

        Raises:
            ValueError: If the line's syntax or metadata is invalid.
        """
        line_data = line.split(':', maxsplit=1)
        if len(line_data) != 2:
            raise ValueError("Invalid line syntax, wrong number of ':' "
                             "detected in zone connection info")
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
                raise ValueError("Invalid metadata format, missing "
                                 "closing ']'")
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
