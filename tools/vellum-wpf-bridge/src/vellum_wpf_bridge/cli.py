"""Command-Line Interface (CLI) for Vellum to WPF Bridge."""

import argparse
import json
from pathlib import Path
import sys
from typing import Optional

from .models import UiSpec
from .refiner import SafeAgentRefiner
from .report import ConversionReport
from .resources import ResourceManager
from .semantic_mapper import SemanticMapper
from .validator import validate_vellum_file
from .vellum_adapter import VellumDocumentAdapter
from .wpf_generator import WpfGenerator


def _write_generated(out_path, generated_files):
    for filename, content in generated_files.items():
        destination = out_path / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            destination.write_bytes(content)
        else:
            destination.write_text(content, encoding="utf-8")
        print(f"      Saved: {destination}")


def validate(input_file: str) -> int:
    """Validate a .vellum document against strict specification constraints."""
    in_path = Path(input_file)
    if not in_path.exists():
        print(f"Error: Input file not found: {in_path}", file=sys.stderr)
        return 1
    try:
        validate_vellum_file(in_path)
        print(f"PASS: {in_path.name} is a valid Vellum document.")
        return 0
    except Exception as e:
        print(f"FAIL: {in_path.name}: {e}", file=sys.stderr)
        return 1


def convert(
    input_file: str,
    output_dir: str = "output",
    spec_only: bool = False,
    page_index: int = 0,
    app_namespace: str = "GeneratedWpfDemo",
    patch_file: Optional[str] = None,
) -> int:
    """Execute conversion pipeline from .vellum to Semantic UI Spec and WPF/XAML."""
    in_path = Path(input_file)
    if not in_path.exists():
        print(f"Error: Input file not found: {in_path}", file=sys.stderr)
        return 1

    out_path = Path(output_dir)

    print(f"[1/4] Reading and normalizing Vellum document: {in_path.name}...")
    adapter = VellumDocumentAdapter()
    try:
        doc = adapter.load_from_file(in_path)
    except Exception as e:
        print(f"Error parsing .vellum file: {e}", file=sys.stderr)
        return 1

    print(f"      Document '{doc.name}' loaded with {len(doc.pages)} pages.")

    print(f"[2/4] Mapping design to Semantic UI Spec (Page #{page_index})...")
    report = ConversionReport()
    mapper = SemanticMapper(report=report)
    spec = mapper.map_document(doc, page_index=page_index)

    refinement_report = None
    try:
        if patch_file:
            patch = json.loads(Path(patch_file).read_text(encoding="utf-8"))
            refined, refinement_report = SafeAgentRefiner().apply_patch(spec.to_dict(), patch)
            spec = UiSpec.from_dict(refined)
        else:
            spec = UiSpec.from_dict(spec.to_dict())
    except (ValueError, OSError) as e:
        print(f"Error validating/refining converted spec: {e}", file=sys.stderr)
        return 1

    out_path.mkdir(parents=True, exist_ok=True)
    if refinement_report:
        refinement_report.save_to_file(out_path / "refinement-report.json")

    # Save ui-spec.json
    ui_spec_file = out_path / "ui-spec.json"
    with open(ui_spec_file, "w", encoding="utf-8") as f:
        json.dump(spec.to_dict(), f, indent=2, ensure_ascii=False)
    print(f"      Saved: {ui_spec_file}")

    if spec_only:
        # Save conversion report
        report_file = out_path / "conversion-report.json"
        report.save_to_file(report_file)
        print(f"      Saved: {report_file}")
        print("Done (--spec-only requested).")
        return 0

    print("[3/4] Generating WPF/XAML markup directly from Semantic UI Spec...")
    generator = WpfGenerator(report=report)
    generated_files = generator.generate_all(spec, app_namespace=app_namespace)
    for note in generator.rm.inferred_token_notes:
        report.add_diagnostic("note", "TOKEN_INFERRED_BY_VALUE", note)

    _write_generated(out_path, generated_files)

    print("[4/4] Writing conversion report...")
    report_file = out_path / "conversion-report.json"
    report.save_to_file(report_file)
    print(f"      Saved: {report_file}")

    print("\nConversion Summary:")
    print(f"  - Total nodes:     {report.nodes_total}")
    print(f"  - Converted:       {report.nodes_converted}")
    print(f"  - Absorbed:        {report.nodes_absorbed}")
    print(f"  - Fallback nodes:  {report.nodes_fallback}")
    print(f"  - Unsupported:     {len(report.unsupported)}")
    print(f"  - Diagnostics:     {len(report.diagnostics)}")

    return 0


def generate(
    spec_file: str,
    output_dir: str = "output",
    app_namespace: str = "GeneratedWpfDemo",
) -> int:
    """Generate WPF/XAML markup directly from Semantic UI Spec (ui-spec.json)."""
    in_path = Path(spec_file)
    if not in_path.exists():
        print(f"Error: Spec file not found: {in_path}", file=sys.stderr)
        return 1

    out_path = Path(output_dir)

    print(f"[1/2] Loading Semantic UI Spec: {in_path.name}...")
    try:
        with open(in_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        spec = UiSpec.from_dict(data)
    except Exception as e:
        print(f"Error parsing UI spec: {e}", file=sys.stderr)
        return 1

    print(f"      Spec '{spec.name}' loaded successfully.")
    print("[2/2] Generating WPF/XAML markup...")
    generator = WpfGenerator()
    try:
        generated_files = generator.generate_all(spec, app_namespace=app_namespace)
    except ValueError as e:
        print(f"Error generating UI spec: {e}", file=sys.stderr)
        return 1
    out_path.mkdir(parents=True, exist_ok=True)
    _write_generated(out_path, generated_files)
    print("Done (WPF/XAML generated from ui-spec.json).")
    return 0


def refine_validate(spec_file: str, patch_file: str) -> int:
    """Validate an agent refinement patch against a base Semantic UI Spec."""
    s_path = Path(spec_file)
    p_path = Path(patch_file)
    if not s_path.exists():
        print(f"Error: Spec file not found: {s_path}", file=sys.stderr)
        return 1
    if not p_path.exists():
        print(f"Error: Patch file not found: {p_path}", file=sys.stderr)
        return 1

    try:
        with open(s_path, "r", encoding="utf-8") as f:
            spec_data = json.load(f)
        with open(p_path, "r", encoding="utf-8") as f:
            patch_data = json.load(f)
        refiner = SafeAgentRefiner()
        notes = refiner.validate_patch(spec_data, patch_data)
        for note in notes:
            print(f"PASS: {note}")
        return 0
    except Exception as e:
        print(f"FAIL: Patch validation failed: {e}", file=sys.stderr)
        return 1


def refine_apply(
    spec_file: str,
    patch_file: str,
    output_dir: str = "output",
    output_spec: str = "refined-ui-spec.json",
    report_file: str = "refinement-report.json",
) -> int:
    """Apply an agent refinement patch to a base Semantic UI Spec, generating refined spec and report."""
    s_path = Path(spec_file)
    p_path = Path(patch_file)
    if not s_path.exists():
        print(f"Error: Spec file not found: {s_path}", file=sys.stderr)
        return 1
    if not p_path.exists():
        print(f"Error: Patch file not found: {p_path}", file=sys.stderr)
        return 1

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    try:
        with open(s_path, "r", encoding="utf-8") as f:
            spec_data = json.load(f)
        with open(p_path, "r", encoding="utf-8") as f:
            patch_data = json.load(f)
        refiner = SafeAgentRefiner()
        refined_spec, report = refiner.apply_patch(spec_data, patch_data)

        out_spec_file = out_path / output_spec
        with open(out_spec_file, "w", encoding="utf-8") as f:
            json.dump(refined_spec, f, indent=2, ensure_ascii=False)
        print(f"Saved refined UI spec: {out_spec_file}")

        out_rep_file = out_path / report_file
        report.save_to_file(out_rep_file)
        print(f"Saved refinement audit report: {out_rep_file}")
        print(f"Successfully applied {len(report.changes)} refinement operations.")
        return 0
    except Exception as e:
        print(f"Error applying patch: {e}", file=sys.stderr)
        return 1


def main():
    parser = argparse.ArgumentParser(
        prog="vellum-wpf",
        description="Vellum to Semantic UI Spec to WPF/XAML Bridge Converter & Refiner",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # validate command
    val_parser = subparsers.add_parser("validate", help="Validate .vellum document syntax and structure")
    val_parser.add_argument("input", help="Path to input .vellum file")

    # convert command
    conv_parser = subparsers.add_parser("convert", help="Convert .vellum to UI Spec and WPF/XAML")
    conv_parser.add_argument("input", help="Path to input .vellum file")
    conv_parser.add_argument(
        "-o", "--output", default="output", help="Output directory (default: output)"
    )
    conv_parser.add_argument(
        "--spec-only",
        action="store_true",
        help="Only generate Semantic UI Spec (ui-spec.json)",
    )
    conv_parser.add_argument(
        "--page", type=int, default=0, help="Page index to convert (default: 0)"
    )
    conv_parser.add_argument(
        "--namespace",
        default="GeneratedWpfDemo",
        help="C# namespace for XAML code-behind (default: GeneratedWpfDemo)",
    )

    conv_parser.add_argument("--patch", help="Apply a canonical-hash-verified agent patch after mapping")

    # generate command
    gen_parser = subparsers.add_parser(
        "generate", help="Generate WPF/XAML directly from ui-spec.json"
    )
    gen_parser.add_argument("spec", help="Path to input ui-spec.json file")
    gen_parser.add_argument(
        "-o", "--output", default="output", help="Output directory (default: output)"
    )
    gen_parser.add_argument(
        "--namespace",
        default="GeneratedWpfDemo",
        help="C# namespace for XAML code-behind (default: GeneratedWpfDemo)",
    )

    # refine-validate command
    rv_parser = subparsers.add_parser(
        "refine-validate", help="Validate an agent refinement patch against ui-spec.json"
    )
    rv_parser.add_argument("spec", help="Path to base ui-spec.json")
    rv_parser.add_argument("patch", help="Path to agent-patch.json")

    # refine-apply command
    ra_parser = subparsers.add_parser(
        "refine-apply", help="Atomically apply an agent refinement patch to ui-spec.json"
    )
    ra_parser.add_argument("spec", help="Path to base ui-spec.json")
    ra_parser.add_argument("patch", help="Path to agent-patch.json")
    ra_parser.add_argument(
        "-o", "--output", default="output", help="Output directory (default: output)"
    )
    ra_parser.add_argument(
        "--output-spec",
        default="refined-ui-spec.json",
        help="Output refined spec filename (default: refined-ui-spec.json)",
    )
    ra_parser.add_argument(
        "--report",
        default="refinement-report.json",
        help="Output refinement audit report filename (default: refinement-report.json)",
    )

    args = parser.parse_args()
    if args.command == "validate":
        sys.exit(validate(input_file=args.input))
    elif args.command == "convert":
        sys.exit(
            convert(
                input_file=args.input,
                output_dir=args.output,
                spec_only=args.spec_only,
                patch_file=args.patch,
                page_index=args.page,
                app_namespace=args.namespace,
            )
        )
    elif args.command == "generate":
        sys.exit(
            generate(
                spec_file=args.spec,
                output_dir=args.output,
                app_namespace=args.namespace,
            )
        )
    elif args.command == "refine-validate":
        sys.exit(refine_validate(spec_file=args.spec, patch_file=args.patch))
    elif args.command == "refine-apply":
        sys.exit(
            refine_apply(
                spec_file=args.spec,
                patch_file=args.patch,
                output_dir=args.output,
                output_spec=args.output_spec,
                report_file=args.report,
            )
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
