"""Utility functions for name formatting, colors, and XML formatting."""

import re
from typing import Optional, Tuple


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
    """Normalize hex colors like #fff, #ffffff, #rrggbbaa to #AARRGGBB for WPF."""
    if not color_str or color_str.lower() == "none":
        return None

    raw = color_str.strip().lstrip("#")
    if len(raw) == 3:  # rgb -> ffffffff
        r, g, b = raw[0], raw[1], raw[2]
        return f"#{r}{r}{g}{g}{b}{b}".upper()
    elif len(raw) == 6:  # rrggbb -> #rrggbb (WPF accepts #RRGGBB)
        return f"#{raw}".upper()
    elif len(raw) == 8:  # rrggbbaa -> #AARRGGBB (WPF format)
        rr, gg, bb, aa = raw[0:2], raw[2:4], raw[4:6], raw[6:8]
        return f"#{aa}{rr}{gg}{bb}".upper()

    return f"#{raw}".upper()


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


def fmt_length(value) -> str:
    """Format a track size or pixel length for XAML / JSON-adjacent output."""
    if value == "*" or value == "Auto":
        return str(value)
    if isinstance(value, str):
        return value
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return str(number)
