"""Application service orchestrating the existing eight-stage POC pipeline."""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TextIO

from app.ai.client import make_client
from app.ai.prompts.constraints import extract_constraints
from app.ai.prompts.critique import critique_draft
from app.ai.prompts.drafting import draft_issues
from app.ai.prompts.styling import normalise_style_spec, produce_style_spec
from app.ai.validation import build_validation
from app.application.pipeline_versioning import next_version
from app.core.config import load_config
from app.documents.parsers import parse_folder, persist_parsed
from app.documents.render import render
from app.documents.template_inspector import inspect_templates
from app.rag.context import HELD_OUT_FILENAMES, build_context

TOTAL_STEPS = 8


class PipelineInputError(ValueError):
    """Raised when a pipeline request references invalid local input."""


@dataclass(frozen=True)
class PipelineRequest:
    project_path: Path
    issues_path: Path | None = None
    auditor_input: Any | None = None
    version: str | None = None
    run_directory: Path | None = None
    project_name: str | None = None


@dataclass(frozen=True)
class PipelineProgress:
    stage: str
    message: str
    completed_steps: int
    total_steps: int = TOTAL_STEPS
    warning: bool = False


@dataclass(frozen=True)
class PipelineResult:
    version: str
    run_directory: Path
    output_path: Path
    issue_count: int


ProgressReporter = Callable[[PipelineProgress], None]


def _write_log(log: TextIO, stage: str, message: str) -> None:
    timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log.write(f"{timestamp} [{stage:<12}] {message}\n")
    log.flush()


def _emit(
    reporter: ProgressReporter | None,
    stage: str,
    message: str,
    completed_steps: int,
    *,
    warning: bool = False,
) -> None:
    if reporter is not None:
        reporter(
            PipelineProgress(
                stage=stage,
                message=message,
                completed_steps=completed_steps,
                warning=warning,
            )
        )


def _read_auditor_input(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PipelineInputError(
            f"--issues {path} is not valid JSON: {exc}"
        ) from exc


def _project_display_name(project_path: Path) -> str:
    raw_name = project_path.name.replace("_", " ").replace("-", " ").strip()
    return " ".join(word.capitalize() for word in raw_name.split())


class AuditPipeline:
    """Runs the POC pipeline independently of CLI or HTTP transport."""

    def run(
        self,
        request: PipelineRequest,
        *,
        reporter: ProgressReporter | None = None,
    ) -> PipelineResult:
        project_path = request.project_path.resolve()
        if not project_path.is_dir():
            raise PipelineInputError(
                f"--project {project_path} is not a directory"
            )
        if request.auditor_input is not None:
            auditor_input = request.auditor_input
        elif request.issues_path is not None:
            issues_path = request.issues_path.resolve()
            if not issues_path.is_file():
                raise PipelineInputError(
                    f"--issues {issues_path} is not a file"
                )
            auditor_input = _read_auditor_input(issues_path)
        else:
            raise PipelineInputError(
                "Pipeline requires auditor_input or an --issues JSON file"
            )
        if not isinstance(auditor_input, list):
            raise PipelineInputError("Auditor input must be a JSON array")

        config = load_config()
        client = make_client(config)
        if request.version is None:
            version, run_directory = next_version(project_path)
        else:
            if request.run_directory is None:
                raise PipelineInputError(
                    "run_directory is required with an external version"
                )
            version = request.version
            run_directory = request.run_directory.resolve()
            run_directory.mkdir(parents=True, exist_ok=False)
        project_name = request.project_name or _project_display_name(
            project_path
        )

        log_path = run_directory / "run.log"
        with log_path.open("w", encoding="utf-8") as log:
            _write_log(
                log,
                "start",
                f"project={project_path} version={version}",
            )

            _emit(reporter, "PARSING", "Parsing project documents...", 0)
            parsed = parse_folder(
                project_path,
                skip_filenames=HELD_OUT_FILENAMES,
            )
            persist_parsed(parsed, run_directory)
            _write_log(log, "parse", f"parsed {len(parsed)} files")
            _emit(
                reporter,
                "PARSING",
                f"Parsed {len(parsed)} project files",
                1,
            )

            _emit(reporter, "CONTEXT", "Building audit context...", 1)
            context = build_context(parsed)
            total_chars = sum(len(value) for value in context.blobs.values())
            _write_log(
                log,
                "context",
                f"assembled {total_chars:,} chars; FY2024 held out",
            )
            for line in context.truncation_log:
                _write_log(log, "context", f"WARN: {line}")
                _emit(reporter, "CONTEXT", line, 2, warning=True)
            _emit(reporter, "CONTEXT", "Audit context ready", 2)

            _emit(
                reporter,
                "CONSTRAINTS",
                "Extracting scope and constraints...",
                2,
            )
            constraint_result = extract_constraints(
                client,
                config.model,
                awp=context.blobs["AWP"],
                apm=context.blobs["APM"],
            )
            constraints = constraint_result.data
            (run_directory / "constraints.json").write_text(
                json.dumps(constraints, indent=2),
                encoding="utf-8",
            )
            _write_log(
                log,
                "step1",
                "OK. "
                f"in={constraint_result.input_tokens} "
                f"out={constraint_result.output_tokens} tokens",
            )
            _emit(reporter, "CONSTRAINTS", "Scope constraints extracted", 3)

            _emit(reporter, "DRAFTING", "Drafting audit issues...", 3)
            draft_result = draft_issues(
                client,
                config.model,
                constraints=constraints,
                guidelines=context.blobs["GUIDELINES"],
                samples=context.blobs["SAMPLES"],
                sop=context.blobs["SOP"],
                process_understanding=context.blobs["PROCESS_UNDERSTANDING"],
                auditor_input=auditor_input,
            )
            draft = draft_result.data
            (run_directory / "draft.json").write_text(
                json.dumps(draft, indent=2),
                encoding="utf-8",
            )
            _write_log(
                log,
                "step2",
                "OK. "
                f"in={draft_result.input_tokens} "
                f"out={draft_result.output_tokens} tokens, "
                f"{len(draft)} issues",
            )
            _emit(
                reporter,
                "DRAFTING",
                f"Drafted {len(draft)} issues",
                4,
            )

            _emit(reporter, "CRITIQUING", "Reviewing draft quality...", 4)
            critique_result = critique_draft(
                client,
                config.model,
                constraints=constraints,
                guidelines=context.blobs["GUIDELINES"],
                sop=context.blobs["SOP"],
                process_understanding=context.blobs["PROCESS_UNDERSTANDING"],
                draft=draft,
            )
            _write_log(
                log,
                "step3",
                "OK. "
                f"in={critique_result.input_tokens} "
                f"out={critique_result.output_tokens} tokens",
            )
            _emit(reporter, "CRITIQUING", "Draft quality review complete", 5)

            _emit(reporter, "STYLING", "Producing DOCX style spec...", 5)
            template_paths = [project_path / "Output" / "template.docx"]
            samples_directory = project_path / "Samples"
            if samples_directory.is_dir():
                template_paths.extend(
                    sorted(
                        path
                        for path in samples_directory.glob("*.docx")
                        if not path.name.startswith("~$")
                    )
                )
            template_analysis = inspect_templates(template_paths)
            if not template_analysis:
                warning = "No template files found; using defaults"
                _write_log(log, "step4", f"WARN: {warning}")
                _emit(reporter, "STYLING", warning, 5, warning=True)

            style_spec = None
            try:
                style_result = produce_style_spec(
                    client,
                    config.model,
                    guidelines=context.blobs["GUIDELINES"],
                    template_analysis=template_analysis,
                    draft=draft,
                )
                style_spec = style_result.data
                _write_log(
                    log,
                    "step4",
                    "OK. "
                    f"in={style_result.input_tokens} "
                    f"out={style_result.output_tokens} tokens",
                )
            except Exception as exc:
                warning = f"LLM styling failed ({exc}); using defaults"
                _write_log(log, "step4", f"WARN: {warning}")
                _emit(reporter, "STYLING", warning, 5, warning=True)

            style_spec = normalise_style_spec(
                style_spec,
                template_analysis or None,
            )
            (run_directory / "style_spec.json").write_text(
                json.dumps(style_spec, indent=2),
                encoding="utf-8",
            )
            _emit(reporter, "STYLING", "DOCX style spec ready", 6)

            _emit(reporter, "VALIDATING", "Validating draft issues...", 6)
            validation = build_validation(
                draft=draft,
                constraints=constraints,
                llm_critique=critique_result.data,
                context_truncated=context.truncated,
            )
            (run_directory / "validation.json").write_text(
                json.dumps(validation, indent=2),
                encoding="utf-8",
            )
            rule_based = validation["rule_based"]
            _write_log(
                log,
                "validate",
                "rule_based "
                f"passed={rule_based['passed']} "
                f"warnings={len(rule_based['warnings'])}",
            )
            _emit(reporter, "VALIDATING", "Draft validation complete", 7)

            _emit(reporter, "RENDERING", "Generating DOCX...", 7)
            output_path = (
                run_directory / f"{project_name}_Issue Log {version}.docx"
            )
            entity_legal = constraints.get("entity_legal_name") or ""
            if not entity_legal:
                entities = constraints.get("audited_entities") or []
                entity_legal = next(
                    (
                        entity
                        for entity in entities
                        if "Ltd" in entity or "Pte" in entity
                    ),
                    entities[0] if entities else "",
                )
            render(
                draft,
                project_name=project_name,
                version=version,
                out_path=output_path,
                style_spec=style_spec,
                entity_legal=entity_legal,
                fiscal_year=constraints.get("fiscal_year") or "",
                review_procedures=constraints.get("review_procedures") or [],
            )
            _write_log(log, "render", f"wrote {output_path}")
            _emit(reporter, "RENDERING", "DOCX generated", 8)

        return PipelineResult(
            version=version,
            run_directory=run_directory,
            output_path=output_path,
            issue_count=len(draft),
        )
