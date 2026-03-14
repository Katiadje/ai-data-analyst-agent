"""Analysis endpoints — trigger and retrieve analysis results."""

import os
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from agent.analyst_agent import run_analysis
from api.models import AnalysisResponse, ChartInfo

router = APIRouter()

UPLOADS_DIR = os.environ.get("UPLOADS_DIR", "/tmp/ai_analyst_uploads")
OUTPUTS_DIR = os.environ.get("OUTPUTS_DIR", "/tmp/ai_analyst_outputs")

_jobs: dict[str, dict] = {}


def _find_upload(session_id: str) -> str | None:
    """Find uploaded file by session_id (any supported extension)."""
    for ext in (".csv", ".xlsx", ".xls"):
        path = os.path.join(UPLOADS_DIR, f"{session_id}{ext}")
        if os.path.exists(path):
            return path
    return None


def _run_job(session_id: str, file_path: str, base_url: str):
    """Background task: run the agent pipeline and store results."""
    output_dir = os.path.join(OUTPUTS_DIR, session_id)
    os.makedirs(output_dir, exist_ok=True)

    _jobs[session_id] = {"status": "running", "progress": 0, "current_step": "Starting..."}

    try:
        result = run_analysis(file_path, output_dir, session_id=session_id)

        for chart in result.get("charts", []):
            rel_path = os.path.relpath(chart["path"], OUTPUTS_DIR)
            chart["url"] = f"{base_url}/outputs/{rel_path}"

        _jobs[session_id] = result
    except Exception as e:
        _jobs[session_id] = {
            "status": "error",
            "progress": 0,
            "current_step": "Failed",
            "error": str(e),
            "profile": {},
            "insights": {},
            "charts": [],
            "report_md": "",
        }


@router.post(
    "/analyse/{session_id}",
    response_model=AnalysisResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start analysis for an uploaded file",
)
async def start_analysis(
    session_id: str, request: Request, background_tasks: BackgroundTasks
) -> AnalysisResponse:
    file_path = _find_upload(session_id)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No uploaded file found for session '{session_id}'. Upload first.",
        )

    if session_id in _jobs and _jobs[session_id].get("status") == "running":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Analysis already running for this session.",
        )

    base_url = str(request.base_url).rstrip("/")
    background_tasks.add_task(_run_job, session_id, file_path, base_url)
    _jobs[session_id] = {"status": "running", "progress": 0, "current_step": "Queued"}

    return AnalysisResponse(
        session_id=session_id,
        status="running",
        progress=0,
        current_step="Queued — analysis starting",
    )


@router.get(
    "/analyse/{session_id}",
    response_model=AnalysisResponse,
    summary="Get analysis status and results",
)
async def get_analysis(session_id: str) -> AnalysisResponse:
    if session_id not in _jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No analysis found for session '{session_id}'.",
        )

    job = _jobs[session_id]

    charts = [
        ChartInfo(
            id=c.get("id", uuid.uuid4().hex[:8]),
            title=c.get("title", "Chart"),
            path=c.get("path", ""),
            url=c.get("url", ""),
            description=c.get("description", ""),
        )
        for c in job.get("charts", [])
    ]

    return AnalysisResponse(
        session_id=session_id,
        status=job.get("status", "unknown"),
        progress=job.get("progress", 0),
        current_step=job.get("current_step", ""),
        profile=job.get("profile", {}),
        insights=job.get("insights", {}),
        charts=charts,
        report_md=job.get("report_md", ""),
        duration_s=job.get("duration_s"),
        error=job.get("error"),
    )


@router.delete(
    "/analyse/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete analysis session and all generated files",
)
async def delete_analysis(session_id: str):
    _jobs.pop(session_id, None)

    output_dir = os.path.join(OUTPUTS_DIR, session_id)
    if os.path.exists(output_dir):
        import shutil
        shutil.rmtree(output_dir, ignore_errors=True)

    for ext in (".csv", ".xlsx", ".xls"):
        path = os.path.join(UPLOADS_DIR, f"{session_id}{ext}")
        if os.path.exists(path):
            os.remove(path)
