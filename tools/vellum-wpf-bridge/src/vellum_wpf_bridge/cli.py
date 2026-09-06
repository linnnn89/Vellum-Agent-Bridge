"""Command-Line Interface (CLI) for Vellum to WPF Bridge."""

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Optional

from .models import UiSpecRefiner
from .report import ConversionReport
from .resources import ResourceManager
from .semantic_mapper import SemanticMapper
from .vellum_adapter import VellumDocumentAdapter
from .wpf_generator import WpfGenerator


def convert(
    input_file: str,
    output_dir: str = "output",
    spec_only: bool = False,
    page_index: int = 0,
    app_namespace: str = "GeneratedWpfDemo",
) -> int:
    """Execute conversion pipeline from .vellum to Semantic UI Spec and WPF/XAML."""
    in_path = Path(input_file)
    if not in_path.exists():
        print(f"Error: Input file not found: {in_path}", file=sys.stderr)
        return 1

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

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

    # Apply AI refiner extension hook (stub)
    refiner = UiSpecRefiner()
    spec = refiner.refine(spec)

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

    print("[3/4] Generating WPF/XAML markup...")
    rm = ResourceManager()
    rm.extract_from_document_tokens(doc)
    generator = WpfGenerator(resource_manager=rm)
    generated_files = generator.generate_all(spec, app_namespace=app_namespace)
    for note in rm.inferred_token_notes:
        report.add_diagnostic("note", "TOKEN_INFERRED_BY_VALUE", note)

    for filename, content in generated_files.items():
        file_dest = out_path / filename
        with open(file_dest, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"      Saved: {file_dest}")

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


def main():
    parser = argparse.ArgumentParser(
        prog="vellum-wpf",
        description="Vellum to Semantic UI Spec to WPF/XAML Bridge Converter",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

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

    args = parser.parse_args()
    if args.command == "convert":
        sys.exit(
            convert(
                input_file=args.input,
                output_dir=args.output,
                spec_only=args.spec_only,
                page_index=args.page,
                app_namespace=args.namespace,
            )
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
