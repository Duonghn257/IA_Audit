"""Compatibility CLI adapter for the audit pipeline."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.application.audit_pipeline import (
    AuditPipeline,
    PipelineInputError,
    PipelineProgress,
    PipelineRequest,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Draft an Internal Audit issue log from a project folder.",
    )
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--issues", required=True, type=Path)
    return parser.parse_args(argv)


def _print_progress(progress: PipelineProgress) -> None:
    marker = (
        f"[{progress.completed_steps}/{progress.total_steps}]"
        if progress.total_steps
        else f"[{progress.stage}]"
    )
    print(f"{marker} {progress.message}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    request = PipelineRequest(
        project_path=args.project,
        issues_path=args.issues,
    )

    try:
        result = AuditPipeline().run(request, reporter=_print_progress)
    except PipelineInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: pipeline failed: {exc}", file=sys.stderr)
        return 1

    print(f"\n-> {result.output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
