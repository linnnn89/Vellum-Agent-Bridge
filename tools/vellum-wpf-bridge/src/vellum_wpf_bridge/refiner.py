"""Safe Agent Refiner for Semantic UI Spec.

Enables agents/LLMs to modify semantic intent (commands, tooltips, accessible labels, text)
while strictly locking down layout, style, hierarchy, and design constraints.
"""

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .models import UiSpec
from .utils import is_binding_identifier
from .spec_validator import validate_ui_spec_dict, UiSpecValidationError


ALLOWED_PATCH_PATHS: Set[str] = {
    "name",
    "props.text",
    "props.command",
    "props.tooltip",
    "props.accessibleName",
    "props.helpText",
    "props.semanticRole",
}

FORBIDDEN_PREFIXES: Tuple[str, ...] = (
    "id",
    "type",
    "source",
    "layout",
    "style",
    "children",
    "resources",
)

_SHA256_HEX_RE = re.compile(r"^[a-f0-9]{64}$")


class PatchValidationError(ValueError):
    """Raised when an agent refinement patch fails validation."""
    pass


@dataclass
class RefinementChange:
    node_id: str
    path: str
    old_value: Any
    new_value: Any
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodeId": self.node_id,
            "path": self.path,
            "oldValue": {"redacted": True},
            "newValue": {"redacted": True},
            "reason": {"redacted": True},
        }


@dataclass
class RefinementReport:
    version: int = 2
    base_spec_sha256: str = ""
    operations_count: int = 0
    changes: List[RefinementChange] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "baseSpecSha256": self.base_spec_sha256,
            "operationsCount": len(self.changes),
            "changes": [c.to_dict() for c in self.changes],
        }

    def save_to_file(self, file_path: Union[str, Path]):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


def compute_spec_canonical_sha256(spec_dict: Dict[str, Any]) -> str:
    """Compute deterministic SHA256 of canonicalized UI Spec JSON."""
    canonical = json.dumps(spec_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_file_sha256(file_path: Union[str, Path]) -> str:
    """Compute SHA256 of file bytes."""
    return hashlib.sha256(Path(file_path).read_bytes()).hexdigest()


def _collect_node_map(root: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Traverse tree and index all nodes by id."""
    node_map: Dict[str, Dict[str, Any]] = {}
    if not root or not isinstance(root, dict):
        return node_map

    def walk(node: Dict[str, Any]):
        node_id = node.get("id")
        if node_id:
            node_map[node_id] = node
        for child in node.get("children", []):
            if isinstance(child, dict):
                walk(child)

    walk(root)
    return node_map


class SafeAgentRefiner:
    """Validates and atomically applies an agent refinement patch to a UI Spec."""

    def validate_patch(
        self,
        spec_data: Dict[str, Any],
        patch_data: Dict[str, Any],
        raw_file_sha256: Optional[str] = None,
    ) -> List[str]:
        """Validate patch against spec. Returns list of warning/info notes or raises PatchValidationError."""
        try:
            validate_ui_spec_dict(spec_data)
        except UiSpecValidationError as e:
            raise PatchValidationError(f"Invalid base spec: {e}") from e
        if not isinstance(patch_data, dict):
            raise PatchValidationError("Invalid patch format: root must be a JSON object.")

        version = patch_data.get("version")
        if version != 1:
            raise PatchValidationError(f"Unsupported patch version: expected 1, got {version!r}")

        expected_sha = patch_data.get("baseSpecSha256", "")
        if not isinstance(expected_sha, str) or not expected_sha:
            raise PatchValidationError("Patch is missing required 'baseSpecSha256' property.")
        expected_sha = expected_sha.lower()
        if not _SHA256_HEX_RE.fullmatch(expected_sha):
            raise PatchValidationError("Patch 'baseSpecSha256' must be a 64-character hex SHA-256.")

        # Spec identity is canonical JSON only. File-byte hashes are not a
        # document identity: matching raw_file_sha256 would authorize a patch
        # against unrelated bytes and is ignored on purpose.
        _ = raw_file_sha256
        canonical_sha = compute_spec_canonical_sha256(spec_data).lower()
        if expected_sha != canonical_sha:
            raise PatchValidationError(
                f"baseSpecSha256 mismatch! Patch expected '{expected_sha}', but target spec hash is '{canonical_sha}'"
            )

        operations = patch_data.get("operations")
        if not isinstance(operations, list):
            raise PatchValidationError("Patch 'operations' must be an array.")
        if not operations:
            raise PatchValidationError("Patch 'operations' array is empty.")

        node_map = _collect_node_map(spec_data.get("root"))

        for idx, op in enumerate(operations):
            if not isinstance(op, dict):
                raise PatchValidationError(f"Operation at index {idx} must be an object.")

            op_type = op.get("op")
            if op_type != "set":
                raise PatchValidationError(
                    f"Unsupported operation '{op_type}' at index {idx}. Only 'set' is supported."
                )

            node_id = op.get("nodeId")
            if not isinstance(node_id, str) or not node_id:
                raise PatchValidationError(f"Operation at index {idx} has missing or empty 'nodeId'.")
            if node_id not in node_map:
                raise PatchValidationError(
                    f"Operation at index {idx} targets non-existent nodeId '{node_id}'."
                )

            path = op.get("path")
            if not isinstance(path, str) or not path:
                raise PatchValidationError(f"Operation at index {idx} has missing or empty 'path'.")

            # Strictly reject forbidden prefixes
            for forbidden in FORBIDDEN_PREFIXES:
                if path == forbidden or path.startswith(f"{forbidden}."):
                    raise PatchValidationError(
                        f"Disallowed patch path '{path}' at index {idx}. Agent cannot modify design constraint or structure: '{forbidden}'"
                    )

            if path not in ALLOWED_PATCH_PATHS:
                raise PatchValidationError(
                    f"Disallowed patch path '{path}' at index {idx}. Allowed paths: {sorted(ALLOWED_PATCH_PATHS)}"
                )

            reason = op.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                raise PatchValidationError(
                    f"Operation at index {idx} on node '{node_id}' must provide a non-empty 'reason'."
                )

            if "value" not in op:
                raise PatchValidationError(
                    f"Operation at index {idx} on node '{node_id}' missing 'value'."
                )
            _validate_patch_value(path, op["value"], idx, node_id)

        # A syntactically allowed patch must also leave a valid IR. Validate the
        # candidate here so refine-validate and refine-apply agree, without
        # modifying the caller's document or logging any values.
        candidate = deepcopy(spec_data)
        candidate_nodes = _collect_node_map(candidate.get("root"))
        for op in operations:
            target = candidate_nodes[op["nodeId"]]
            if op["path"] == "name":
                target["name"] = op["value"]
            else:
                target.setdefault("props", {})[op["path"][len("props."):]] = op["value"]
        try:
            validate_ui_spec_dict(candidate)
        except ValueError as e:
            raise PatchValidationError(f"Invalid refined spec: {e}") from e
        return [f"Verified {len(operations)} patch operations successfully."]

    def apply_patch(
        self,
        spec_data: Dict[str, Any],
        patch_data: Dict[str, Any],
        raw_file_sha256: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], RefinementReport]:
        """Atomically validate and apply patch. Returns (refined_spec_dict, refinement_report)."""
        # Step 1: Strict validation of all operations before mutating anything
        self.validate_patch(spec_data, patch_data, raw_file_sha256=raw_file_sha256)

        # Step 2: Deep copy for atomic modification
        refined = deepcopy(spec_data)
        node_map = _collect_node_map(refined.get("root"))
        changes: List[RefinementChange] = []

        base_sha = patch_data.get("baseSpecSha256", "")
        operations = patch_data.get("operations", [])

        # Step 3: Apply all operations and record audit changes
        for op in operations:
            node_id = op["nodeId"]
            path = op["path"]
            new_value = op["value"]
            reason = op["reason"]
            target_node = node_map[node_id]

            if path == "name":
                old_value = target_node.get("name")
                target_node["name"] = str(new_value)
            elif path.startswith("props."):
                prop_key = path[len("props."):]
                if "props" not in target_node or not isinstance(target_node["props"], dict):
                    target_node["props"] = {}
                old_value = target_node["props"].get(prop_key)
                target_node["props"][prop_key] = new_value
            else:
                raise PatchValidationError(f"Unhandled allowed path '{path}'")

            changes.append(
                RefinementChange(
                    node_id=node_id,
                    path=path,
                    old_value=old_value,
                    new_value=new_value,
                    reason=reason,
                )
            )

        report = RefinementReport(
            version=2,
            base_spec_sha256=base_sha,
            operations_count=len(changes),
            changes=changes,
        )
        validate_ui_spec_dict(refined)
        return refined, report


def _validate_patch_value(path: str, value: Any, idx: int, node_id: str) -> None:
    """Whitelist value shape. Do not echo payloads: they may contain secrets or markup."""
    if path == "props.command":
        if not is_binding_identifier(value):
            raise PatchValidationError(
                f"Operation at index {idx} on node '{node_id}': "
                "props.command must be a string identifier matching "
                "[A-Za-z_][A-Za-z0-9_]*."
            )
        return
    if not isinstance(value, str):
        raise PatchValidationError(
            f"Operation at index {idx} on node '{node_id}': '{path}' value must be a string."
        )
