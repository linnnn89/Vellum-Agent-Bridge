"""Utility functions for name formatting, colors, and XML formatting."""

import re
import math
from typing import Any, Optional, Tuple

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_HEX_BODY_RE = re.compile(r"^[0-9A-Fa-f]+$")
_BINDING_IDENT_MAX_LEN = 128
_DOTTED_IDENT_MAX_LEN = 256


def is_binding_identifier(value: Any, *, max_len: int = _BINDING_IDENT_MAX_LEN) -> bool:
    """True iff value is a safe ASCII identifier for XAML Binding / x:Name slots."""
    if not isinstance(value, str) or not value or len(value) > max_len:
        return False
    return _IDENT_RE.fullmatch(value) is not None


def is_dotted_identifier(value: Any, *, max_len: int = _DOTTED_IDENT_MAX_LEN) -> bool:
    """True iff value is Identifier or Identifier.Identifier... (namespaces, resource keys)."""
    if not isinstance(value, str) or not value or len(value) > max_len:
        return False
    return all(is_binding_identifier(part) for part in value.split("."))


def to_pascal_case(name: Optional[str]) -> Optional[str]:
    """Convert a human-readable layer name to a valid PascalCase identifier for x:Name.
    
    If the name is generic/meaningless (like 'Rectangle 43', 'Frame 12', 'Group 3'),
    returns None to avoid generating noisy x:Name attributes.
    """
    if not name or not isinstance(name, str):
        return None

    trimmed = name.strip()
    # Check if meaningless/default name like 'Rectangle 12', 'Frame 3', 'Surface', 'Text'
    pattern_generic = re.compile(
        r"^(rectangle|rect|frame|group|ellipse|path|line|text|surface|layer|vector)\s*\d*$",
        re.IGNORECASE,
    )
    if pattern_generic.match(trimmed):
        return None

    # Replace invalid punctuation with spaces
    cleaned = re.sub(r"[^\w\s-]", " ", trimmed)
    # Split into words
    words = re.split(r"[\s_-]+", cleaned)
    words = [w for w in words if w]
    if not words:
        return None

    # Capitalize each word
    pascal = "".join(w[0].upper() + w[1:] for w in words)
    # Ensure starts with letter or underscore
    if pascal and pascal[0].isdigit():
        pascal = "Element" + pascal

    return pascal if pascal else None


def normalize_hex_color(color_str: Optional[str]) -> Optional[str]:
    """Normalize #rgb / #rrggbb / #rrggbbaa to WPF hex. Reject anything else.

    Unknown lengths used to be passed through, which interpolated markup into
    attributes. Color is a hex token, not a free-form XAML fragment.
    """
    if not isinstance(color_str, str):
        return None
    trimmed = color_str.strip()
    if not trimmed or trimmed.lower() == "none":
        return None
    raw = trimmed[1:] if trimmed.startswith("#") else trimmed
    if not _HEX_BODY_RE.fullmatch(raw):
        return None
    if len(raw) == 3:
        r, g, b = raw[0], raw[1], raw[2]
        return f"#{r}{r}{g}{g}{b}{b}".upper()
    if len(raw) == 6:
        return f"#{raw}".upper()
    if len(raw) == 8:
        rr, gg, bb, aa = raw[0:2], raw[2:4], raw[4:6], raw[6:8]
        return f"#{aa}{rr}{gg}{bb}".upper()
    return None


def escape_xml(text: Optional[str]) -> str:
    """Escape XML special characters."""
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def escape_xaml_literal(text: Optional[str]) -> str:
    """Encode a literal, including literal strings that already begin with {}."""
    value = "" if text is None else str(text)
    if value.lstrip().startswith("{"):
        value = "{}" + value
    return escape_xml(value)


def escape_xml_comment(text: str) -> str:
    """Comments cannot contain --, including overlapping runs of hyphens."""
    return re.sub(r"-{2,}", lambda m: "&#45;" * len(m[0]), escape_xml(text))


def normalize_ir_color(color_str: Optional[str]) -> Optional[str]:
    """IR colors are #RGB, #RRGGBB or #AARRGGBB; never rotate alpha again."""
    if not isinstance(color_str, str):
        return None
    value = color_str.strip()
    if re.fullmatch(r"#?[0-9a-fA-F]{8}", value):
        return "#" + value.lstrip("#").upper()
    return normalize_hex_color(value)


def fmt_length(value) -> str:
    """Format a track size or pixel length for XAML / JSON-adjacent output."""
    if value == "*" or value == "Auto":
        return str(value)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Length must be a finite number, '*' or 'Auto'")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Length must be finite")
    if number.is_integer():
        return str(int(number))
    return str(number)
