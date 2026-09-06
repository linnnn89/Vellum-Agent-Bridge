"""Conversion report generator and tracking."""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class UnsupportedItem:
    id: str
    type: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "reason": self.reason,
        }


@dataclass
class Diagnostic:
    severity: str
    code: str
    message: str
    node_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
        }
        if self.node_id:
            d["nodeId"] = self.node_id
        return d


@dataclass
class ConversionReport:
    nodes_total: int = 0
    nodes_converted: int = 0
    nodes_fallback: int = 0
    nodes_absorbed: int = 0
    nodes_skipped: int = 0
    unsupported: List[UnsupportedItem] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    diagnostics: List[Diagnostic] = field(default_factory=list)
    promoted: List[Dict[str, Any]] = field(default_factory=list)
    absorbed: List[Dict[str, Any]] = field(default_factory=list)
    normalized: List[Dict[str, Any]] = field(default_factory=list)

    def record_node(self, converted: bool = True, fallback: bool = False, absorbed: bool = False, skipped: bool = False):
        self.nodes_total += 1
        if absorbed:
            self.nodes_absorbed += 1
        elif skipped:
            self.nodes_skipped += 1
        elif converted and not fallback:
            self.nodes_converted += 1
        else:
            self.nodes_fallback += 1

    def add_unsupported(self, node_id: str, node_type: str, reason: str):
        self.unsupported.append(UnsupportedItem(id=node_id, type=node_type, reason=reason))

    def add_warning(self, warning: str):
        self.warnings.append(warning)

    def add_diagnostic(self, severity: str, code: str, message: str, node_id: Optional[str] = None):
        self.diagnostics.append(
            Diagnostic(severity=severity, code=code, message=message, node_id=node_id)
        )
        self.warnings.append(f"{code}: {message}" if not node_id else f"{code}: {message} ({node_id})")

    def add_promoted(self, node_id: str, source_type: str, target_type: str, reason: str):
        self.promoted.append({
            "id": node_id,
            "from": source_type,
            "to": target_type,
            "reason": reason,
        })

    def add_absorbed(self, node_id: str, parent_id: str, reason: str):
        self.absorbed.append({
            "id": node_id,
            "parentId": parent_id,
            "reason": reason,
        })

    def add_normalized(self, code: str, message: str, node_id: Optional[str] = None):
        item: Dict[str, Any] = {"code": code, "message": message}
        if node_id:
            item["nodeId"] = node_id
        self.normalized.append(item)
        self.add_diagnostic("warning", code, message, node_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodesTotal": self.nodes_total,
            "nodesConverted": self.nodes_converted,
            "nodesFallback": self.nodes_fallback,
            "nodesAbsorbed": self.nodes_absorbed,
            "nodesSkipped": self.nodes_skipped,
            "unsupported": [u.to_dict() for u in self.unsupported],
            "promoted": self.promoted,
            "absorbed": self.absorbed,
            "normalized": self.normalized,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "warnings": self.warnings,
        }

    def save_to_file(self, file_path: Union[str, Path]):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
