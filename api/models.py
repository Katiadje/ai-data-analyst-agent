"""Pydantic models for request/response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    session_id: str
    filename: str
    file_path: str
    size_bytes: int
    message: str = "File uploaded successfully. Run /analyse/{session_id} to start."


class AnalysisRequest(BaseModel):
    session_id: str = Field(..., description="Session ID returned by the upload endpoint")


class ChartInfo(BaseModel):
    id: str
    title: str
    path: str
    url: str
    description: str = ""


class AnalysisResponse(BaseModel):
    session_id: str
    status: str
    progress: int
    current_step: str
    profile: dict[str, Any] = {}
    insights: dict[str, Any] = {}
    charts: list[ChartInfo] = []
    report_md: str = ""
    duration_s: float | None = None
    error: str | None = None


class ErrorResponse(BaseModel):
    detail: str
