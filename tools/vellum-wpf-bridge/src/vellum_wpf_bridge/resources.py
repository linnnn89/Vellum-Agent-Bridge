"""Resource management: color extraction, deduplication, and SolidColorBrush generation."""

import re
from typing import Dict, List, Optional, Set, Tuple
from .models import UiNode, UiSpec, VellumDocument
from .utils import is_dotted_identifier, normalize_hex_color, normalize_ir_color


class ResourceManager:
    """Extracts colors, dedupes them, assigns semantic or clean resource keys,
    and generates XAML resources."""

    def __init__(self):
        # Maps hex_code (#AARRGGBB or #RRGGBB) -> resource_key
        self.color_to_key: Dict[str, str] = {}
        # Maps resource_key -> hex_code
        self.key_to_color: Dict[str, str] = {}
        # Key usage counts
        self.color_counts: Dict[str, int] = {}
        # Token keys inferred by exact color value (Vellum has no per-node tokenId).
        self.inferred_token_keys: Set[str] = set()
        self.inferred_token_notes: List[str] = []

    def load_from_spec(self, spec: UiSpec):
        """Load resources defined directly in UiSpec.resources (self-contained IR)."""
        if not spec or not spec.resources:
            return
        for key, val in spec.resources.items():
            val_norm = normalize_ir_color(val)
            if val_norm:
                res_key = key if key.startswith("Brush.") else self.token_name_to_resource_key(key)
                if not is_dotted_identifier(res_key):
                    continue
                if val_norm not in self.color_to_key:
                    self.color_to_key[val_norm] = res_key
                    self.key_to_color[res_key] = val_norm
                    self.inferred_token_keys.add(res_key)
                    self.inferred_token_notes.append(
                        f"{val_norm} → {res_key} (from UiSpec.resources)"
                    )

    def extract_from_document_tokens(self, doc: VellumDocument):
        """Extract design tokens defined in Vellum document (if present)."""
        tokens = doc.tokens or {}
        color_tokens = tokens.get("colors", [])
        for item in color_tokens:
            name = item.get("name", "")
            val = normalize_hex_color(item.get("value"))
            if val and name:
                key = self.token_name_to_resource_key(name)
                if not is_dotted_identifier(key):
                    continue
                if val not in self.color_to_key:
                    self.color_to_key[val] = key
                    self.key_to_color[key] = val
                    self.inferred_token_keys.add(key)
                    self.inferred_token_notes.append(
                        f"{val} → {key} (exact value match; node does not store tokenId)"
                    )


    def collect_colors_from_tree(self, root: UiNode):
        """Walk UI Spec tree to count color occurrences."""
        def walk(node: UiNode):
            # Check style colors
            for c in [node.style.background, node.style.foreground, node.style.border_color]:
                if c and c.startswith("#"):
                    norm = normalize_ir_color(c)
                    if norm:
                        self.color_counts[norm] = self.color_counts.get(norm, 0) + 1

            for child in node.children:
                walk(child)

        walk(root)

    def finalize_resources(self, min_occurrences: int = 2):
        """Register colors that occur at least min_occurrences times as reusable resources."""
        for color, count in self.color_counts.items():
            if count >= min_occurrences and color not in self.color_to_key:
                clean_hex = color.lstrip("#")
                key = f"Brush.Color_{clean_hex}"
                if not is_dotted_identifier(key):
                    continue
                self.color_to_key[color] = key
                self.key_to_color[key] = color

    def get_color_reference(self, color_hex: Optional[str]) -> Optional[str]:
        """Return {StaticResource Key} if color is a registered resource, else raw hex."""
        if not color_hex:
            return None
        norm = normalize_ir_color(color_hex)
        if not norm:
            return None
        key = self.color_to_key.get(norm)
        if key and is_dotted_identifier(key):
            return f"{{StaticResource {key}}}"
        return norm

    def get_xaml_resource_entries(self, indent: str = "    ") -> List[str]:
        """Generate list of <SolidColorBrush x:Key="..." Color="..."/> strings."""
        entries = []
        for key, color in sorted(self.key_to_color.items()):
            if not is_dotted_identifier(key):
                continue
            if normalize_ir_color(color) is None:
                continue
            entries.append(f'{indent}<SolidColorBrush x:Key="{key}" Color="{color}"/>')
        return entries

    @staticmethod
    def token_name_to_resource_key(token_name: str) -> str:
        # e.g. "Brand / Iris" -> "Brush.Brand.Iris"
        parts = re.split(r"[/_-]+", token_name)
        cleaned_parts = []
        for p in parts:
            words = [w.capitalize() for w in p.strip().split() if w]
            if words:
                cleaned_parts.append("".join(words))
        if cleaned_parts:
            return "Brush." + ".".join(cleaned_parts)
        return f"Brush.{token_name.replace(' ', '')}"

    def _name_to_resource_key(self, token_name: str) -> str:
        return self.token_name_to_resource_key(token_name)

