"""Strict validator for .vellum documents."""

import json
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Set, Union


ID_PATTERN = re.compile(r"^[-_a-zA-Z0-9]{1,128}$")
VALID_NODE_TYPES = {
    "rect", "ellipse", "text", "frame", "group", "path", "line", "image"
}
REQUIRED_NUMERIC_FIELDS = ("x", "y", "w", "h", "rotation", "opacity")


class VellumValidationError(ValueError):
    """Raised when a Vellum document fails strict schema or structural validation."""
    pass


def validate_vellum_dict(data: Any) -> None:
    """Validate raw Vellum JSON dict strictly without silent defaulting.

    Raises VellumValidationError on failure.
    """
    if not isinstance(data, dict):
        raise VellumValidationError("Invalid Vellum document: root must be a JSON object.")

    fmt = data.get("format")
    version = data.get("version")
    if fmt != "vellum" or version != 1:
        raise VellumValidationError(
            f"Unsupported document format: expected format='vellum', version=1. Got format={fmt!r}, version={version!r}"
        )

    pages = data.get("pages")
    if not isinstance(pages, list) or not pages:
        raise VellumValidationError("Invalid Vellum document: 'pages' must be a non-empty array.")
    if len(pages) > 100:
        raise VellumValidationError("Document contains more than 100 pages.")

    all_node_ids: Set[str] = set()
    total_nodes = 0

    for p_idx, page in enumerate(pages):
        if not isinstance(page, dict):
            raise VellumValidationError(f"Invalid page at index {p_idx}: must be an object.")
        page_id = page.get("id")
        if not isinstance(page_id, str) or not ID_PATTERN.match(page_id):
            raise VellumValidationError(f"Invalid or missing page id at index {p_idx}: {page_id!r}")
        page_name = page.get("name")
        if not isinstance(page_name, str):
            raise VellumValidationError(f"Invalid or missing page name at index {p_idx}: {page_name!r}")
        raw_nodes = page.get("nodes")
        if not isinstance(raw_nodes, list):
            raise VellumValidationError(f"Page '{page_id}' has invalid 'nodes': must be an array.")

        total_nodes += len(raw_nodes)
        if total_nodes > 50000:
            raise VellumValidationError("Document exceeds maximum node count of 50,000.")

        page_node_ids: Set[str] = set()
        page_node_map: Dict[str, dict] = {}

        for n_idx, n in enumerate(raw_nodes):
            if not isinstance(n, dict):
                raise VellumValidationError(f"Page '{page_id}' node at index {n_idx} must be an object.")
            node_id = n.get("id")
            if not isinstance(node_id, str) or not ID_PATTERN.match(node_id):
                raise VellumValidationError(
                    f"Page '{page_id}' node at index {n_idx} has invalid id: {node_id!r}"
                )
            if node_id in all_node_ids:
                raise VellumValidationError(f"Duplicate node id '{node_id}' found in document.")
            all_node_ids.add(node_id)
            page_node_ids.add(node_id)
            page_node_map[node_id] = n

            node_type = n.get("type")
            if not isinstance(node_type, str) or node_type.lower() not in VALID_NODE_TYPES:
                raise VellumValidationError(
                    f"Node '{node_id}' has invalid or unsupported type: {node_type!r}"
                )

            # Strictly require x, y, w, h, rotation, opacity as valid finite numbers
            for k in REQUIRED_NUMERIC_FIELDS:
                if k not in n:
                    raise VellumValidationError(
                        f"Node '{node_id}' missing required numeric property: '{k}'"
                    )
                val = n[k]
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    raise VellumValidationError(
                        f"Node '{node_id}' property '{k}' must be a number, got {type(val).__name__}"
                    )
                if not math.isfinite(val) or abs(val) > 1e7:
                    raise VellumValidationError(
                        f"Node '{node_id}' property '{k}' is out of range or non-finite: {val}"
                    )

            if n["w"] < 0 or n["h"] < 0:
                raise VellumValidationError(
                    f"Node '{node_id}' has negative dimensions: w={n['w']}, h={n['h']}"
                )

            # Parent ID validation
            parent_id = n.get("parentId")
            if parent_id is not None:
                if not isinstance(parent_id, str):
                    raise VellumValidationError(
                        f"Node '{node_id}' parentId must be a string if provided."
                    )
                if parent_id == node_id:
                    raise VellumValidationError(
                        f"Node '{node_id}' cannot have itself as parent."
                    )

            if n.get("text") is not None:
                if not isinstance(n["text"], str):
                    raise VellumValidationError(f"Node '{node_id}' text must be a string.")
                if len(n["text"]) > 100000:
                    raise VellumValidationError(f"Node '{node_id}' text exceeds 100,000 characters.")

            if n.get("points") is not None:
                if not isinstance(n["points"], list) or len(n["points"]) > 50000:
                    raise VellumValidationError(f"Node '{node_id}' invalid points array.")

        # Pass 2 for the page: parentId existence and cycle check
        for node_id, n in page_node_map.items():
            parent_id = n.get("parentId")
            if parent_id is not None and parent_id != "":
                if parent_id not in page_node_ids:
                    raise VellumValidationError(
                        f"Node '{node_id}' references non-existent parentId '{parent_id}' in page '{page_id}'."
                    )

            # Cycle & depth check
            seen_ancestors: Set[str] = {node_id}
            curr_parent_id = parent_id
            depth = 0
            while curr_parent_id:
                if curr_parent_id in seen_ancestors:
                    raise VellumValidationError(
                        f"Cyclic hierarchy detected involving node '{node_id}' and ancestor '{curr_parent_id}'."
                    )
                depth += 1
                if depth > 100:
                    raise VellumValidationError(
                        f"Hierarchy depth exceeds 100 for node '{node_id}'."
                    )
                seen_ancestors.add(curr_parent_id)
                curr_parent_id = page_node_map[curr_parent_id].get("parentId")


def validate_vellum_file(file_path: Union[str, Path]) -> None:
    """Read file and validate strictly."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    validate_vellum_dict(data)
