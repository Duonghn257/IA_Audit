"""Project version, issue review and output metadata endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

from app.api.audit_errors import audit_api_errors, feature_unavailable
from app.api.dependencies import (
    get_audit_workspace_service,
    get_discovery_service,
)
from app.api.schemas.audit_issues import (
    CreateManualIssueRequest,
    IssueDispositionRequest,
    IssueResponse,
    UpdateIssueRequest,
)
from app.api.schemas.audit_jobs import (
    JobResponse,
    OutputRevisionResponse,
    StartAuditRequest,
    StartDiscoveryRequest,
)
from app.api.schemas.audit_versions import CreateVersionRequest, ProjectVersionResponse
from app.application.audit_workspace_service import AuditWorkspaceService
from app.application.discovery_service import DiscoveryService

router = APIRouter(prefix="/projects/{project_id}/versions", tags=["audit-workspace"])
AuditServiceDependency = Annotated[AuditWorkspaceService, Depends(get_audit_workspace_service)]
DiscoveryServiceDependency = Annotated[
    DiscoveryService, Depends(get_discovery_service)
]


@router.get("", response_model=list[ProjectVersionResponse])
def list_versions(
    project_id: str,
    service: AuditServiceDependency,
) -> list[ProjectVersionResponse]:
    with audit_api_errors():
        return [
            ProjectVersionResponse.from_domain(item)
            for item in service.list_versions(project_id)
        ]


@router.post("", response_model=ProjectVersionResponse, status_code=status.HTTP_201_CREATED)
def create_version(
    project_id: str,
    request: CreateVersionRequest,
    service: AuditServiceDependency,
) -> ProjectVersionResponse:
    with audit_api_errors():
        workspace = service.create_version(project_id, request.base_version_id)
        return ProjectVersionResponse.from_domain(workspace)


@router.get("/{version_id}", response_model=ProjectVersionResponse)
def get_version(
    project_id: str,
    version_id: str,
    service: AuditServiceDependency,
) -> ProjectVersionResponse:
    with audit_api_errors():
        return ProjectVersionResponse.from_domain(service.get_version(project_id, version_id))


@router.get("/{version_id}/issues", response_model=list[IssueResponse])
def list_issues(
    project_id: str,
    version_id: str,
    service: AuditServiceDependency,
) -> list[IssueResponse]:
    with audit_api_errors():
        service.get_version(project_id, version_id)
        return [IssueResponse.from_domain(item) for item in service.list_issues(version_id)]


@router.post(
    "/{version_id}/issues",
    response_model=IssueResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_issue(
    project_id: str,
    version_id: str,
    request: CreateManualIssueRequest,
    service: AuditServiceDependency,
) -> IssueResponse:
    with audit_api_errors():
        service.get_version(project_id, version_id)
        issue = service.create_manual_issue(
            version_id,
            status=request.status,
            observed_gap=request.observed_gap,
            title_hint=request.title_hint,
            evidence_summary=request.evidence_summary,
            evidence_refs=request.evidence_refs,
            sop_refs=request.sop_refs,
            risk_category=request.risk_category,
            source_refs=[item.to_domain() for item in request.source_refs],
        )
        return IssueResponse.from_domain(issue)


@router.get("/{version_id}/issues/{issue_id}", response_model=IssueResponse)
def get_issue(
    project_id: str,
    version_id: str,
    issue_id: str,
    service: AuditServiceDependency,
) -> IssueResponse:
    with audit_api_errors():
        service.get_version(project_id, version_id)
        return IssueResponse.from_domain(service.get_issue(version_id, issue_id))


@router.put("/{version_id}/issues/{issue_id}", response_model=IssueResponse)
def update_issue(
    project_id: str,
    version_id: str,
    issue_id: str,
    request: UpdateIssueRequest,
    service: AuditServiceDependency,
) -> IssueResponse:
    with audit_api_errors():
        service.get_version(project_id, version_id)
        issue = service.update_issue(
            version_id,
            issue_id,
            expected_row_version=request.row_version,
            status=request.status,
            observed_gap=request.observed_gap,
            title_hint=request.title_hint,
            evidence_summary=request.evidence_summary,
            evidence_refs=request.evidence_refs,
            sop_refs=request.sop_refs,
            risk_category=request.risk_category,
            confidence=request.confidence,
            validation_flags=request.validation_flags,
            source_refs=[item.to_domain() for item in request.source_refs],
        )
        return IssueResponse.from_domain(issue)


@router.post("/{version_id}/issues/{issue_id}/disposition", response_model=IssueResponse)
def set_issue_disposition(
    project_id: str,
    version_id: str,
    issue_id: str,
    request: IssueDispositionRequest,
    service: AuditServiceDependency,
) -> IssueResponse:
    with audit_api_errors():
        service.get_version(project_id, version_id)
        issue = service.set_issue_disposition(
            version_id,
            issue_id,
            expected_row_version=request.row_version,
            status=request.status,
        )
        return IssueResponse.from_domain(issue)


@router.post(
    "/{version_id}/discovery-jobs",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_discovery(
    project_id: str,
    version_id: str,
    request: StartDiscoveryRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    service: AuditServiceDependency,
    discovery: DiscoveryServiceDependency,
) -> JobResponse:
    with audit_api_errors():
        service.get_version(project_id, version_id)
        started = discovery.start_discovery(
            project_id,
            version_id,
            force=request.force,
            correlation_id=http_request.state.correlation_id,
        )
        if started.scheduled:
            background_tasks.add_task(
                discovery.run_discovery, started.job.job_id
            )
        return JobResponse.from_domain(started.job)


@router.post(
    "/{version_id}/audit-jobs",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={501: {"description": "AI audit worker is not implemented"}},
)
def start_audit(
    project_id: str,
    version_id: str,
    request: StartAuditRequest,
    service: AuditServiceDependency,
) -> JobResponse:
    with audit_api_errors():
        workspace = service.get_version(project_id, version_id)
        if workspace.version.issue_revision != request.issue_revision:
            raise ValueError(
                "issue_revision is stale; reload the version before starting an audit."
            )
    raise feature_unavailable(
        "AI_PIPELINE_NOT_IMPLEMENTED",
        "AI audit execution and DOCX generation are not implemented in the MVP yet.",
    )


@router.get("/{version_id}/outputs", response_model=list[OutputRevisionResponse])
def list_outputs(
    project_id: str,
    version_id: str,
    service: AuditServiceDependency,
) -> list[OutputRevisionResponse]:
    with audit_api_errors():
        service.get_version(project_id, version_id)
        return [
            OutputRevisionResponse.from_domain(item)
            for item in service.list_outputs(version_id)
        ]
