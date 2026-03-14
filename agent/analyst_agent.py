"""
AI Data Analyst Agent — LangGraph Orchestration.

Pipeline:
  load → profile → insights → plan_viz → generate_viz → write_report → done
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph

from agent.prompts import (
    CODE_GENERATOR_PROMPT,
    DATA_PROFILER_PROMPT,
    INSIGHTS_PROMPT,
    REPORT_WRITER_PROMPT,
    VIZ_PLANNER_PROMPT,
)
from agent.tools import (
    execute_viz_code,
    generate_overview_charts,
    get_dataset_summary,
    load_dataframe,
)

logger = logging.getLogger(__name__)


# ── State ─────────────────────────────────────────────────────────────────────


@dataclass
class AnalysisState:
    """Shared state across all agent nodes."""

    file_path: str = ""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    output_dir: str = ""
    status: str = "pending"
    current_step: str = ""
    progress: int = 0
    error: str | None = None
    dataset_summary: dict[str, Any] = field(default_factory=dict)
    profile: dict[str, Any] = field(default_factory=dict)
    insights: dict[str, Any] = field(default_factory=dict)
    viz_plan: dict[str, Any] = field(default_factory=dict)
    charts: list[dict[str, str]] = field(default_factory=list)
    report_md: str = ""
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "current_step": self.current_step,
            "progress": self.progress,
            "error": self.error,
            "profile": self.profile,
            "insights": self.insights,
            "charts": self.charts,
            "report_md": self.report_md,
            "duration_s": (
                round(self.completed_at - self.started_at, 2) if self.completed_at else None
            ),
        }


# ── LLM Helpers ───────────────────────────────────────────────────────────────


def _build_llm(model: str = "llama-3.3-70b-versatile", temperature: float = 0.2) -> ChatGroq:
    return ChatGroq(
        model=model,
        temperature=temperature,
        api_key=os.environ["OPENAI_API_KEY"],
    )


def _call_llm_json(llm: ChatGroq, system: str, user: str) -> dict[str, Any]:
    """Call LLM and parse JSON response. Raises on parse failure."""
    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    text = response.content.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


# ── Node Functions ─────────────────────────────────────────────────────────────


def node_load(state: AnalysisState) -> AnalysisState:
    logger.info("[node_load] Loading dataset: %s", state.file_path)
    state.current_step = "Loading dataset"
    state.progress = 5
    state.status = "running"

    try:
        df = load_dataframe(state.file_path)
        summary = get_dataset_summary(df)
        state.dataset_summary = summary
        parquet_path = os.path.join(state.output_dir, "_df.parquet")
        df.to_parquet(parquet_path, index=False)
        state.progress = 15
    except Exception as e:
        state.status = "error"
        state.error = f"Failed to load dataset: {e}"
        logger.exception("Load failed")

    return state


def node_profile(state: AnalysisState) -> AnalysisState:
    if state.status == "error":
        return state

    logger.info("[node_profile] Profiling dataset")
    state.current_step = "Profiling dataset"
    state.progress = 25

    llm = _build_llm(temperature=0.0)
    user_msg = f"Dataset summary:\n{json.dumps(state.dataset_summary, default=str, indent=2)}"

    try:
        profile = _call_llm_json(llm, DATA_PROFILER_PROMPT, user_msg)
        state.profile = profile
        state.progress = 40
    except Exception as e:
        logger.warning("LLM profiling failed, using raw summary. Error: %s", e)
        state.profile = {
            "shape": state.dataset_summary.get("shape", {}),
            "column_profiles": state.dataset_summary.get("columns", []),
            "data_quality_score": 70.0,
            "quality_issues": [],
            "key_observations": ["Profile generated from raw dataset summary."],
        }
        state.progress = 40

    return state


def node_insights(state: AnalysisState) -> AnalysisState:
    if state.status == "error":
        return state

    logger.info("[node_insights] Generating insights")
    state.current_step = "Generating insights"
    state.progress = 50

    llm = _build_llm(temperature=0.3)
    user_msg = (
        f"Dataset profile:\n{json.dumps(state.profile, indent=2)}\n\n"
        f"Sample data:\n{json.dumps(state.dataset_summary.get('sample', []), default=str, indent=2)}\n\n"
        f"Correlations:\n{json.dumps(state.dataset_summary.get('correlation_matrix', {}), indent=2)}"
    )

    try:
        insights = _call_llm_json(llm, INSIGHTS_PROMPT, user_msg)
        state.insights = insights
        state.progress = 60
    except Exception as e:
        logger.warning("Insights generation failed: %s", e)
        state.insights = {
            "executive_summary": "Automated analysis completed.",
            "key_insights": [],
            "recommended_analyses": [],
            "business_implications": [],
        }
        state.progress = 60

    return state


def node_plan_viz(state: AnalysisState) -> AnalysisState:
    if state.status == "error":
        return state

    logger.info("[node_plan_viz] Planning visualizations")
    state.current_step = "Planning visualizations"
    state.progress = 65

    llm = _build_llm(temperature=0.2)
    user_msg = (
        f"Profile:\n{json.dumps(state.profile, indent=2)}\n\n"
        f"Insights:\n{json.dumps(state.insights, indent=2)}\n\n"
        f"Available columns: {[c['name'] for c in state.dataset_summary.get('columns', [])]}"
    )

    try:
        viz_plan = _call_llm_json(llm, VIZ_PLANNER_PROMPT, user_msg)
        state.viz_plan = viz_plan
        state.progress = 70
    except Exception as e:
        logger.warning("Viz planning failed: %s", e)
        state.viz_plan = {"visualizations": []}
        state.progress = 70

    return state


def node_generate_viz(state: AnalysisState) -> AnalysisState:
    if state.status == "error":
        return state

    logger.info("[node_generate_viz] Generating visualizations")
    state.current_step = "Generating visualizations"
    state.progress = 72

    import pandas as pd

    parquet_path = os.path.join(state.output_dir, "_df.parquet")
    df = pd.read_parquet(parquet_path)

    charts = generate_overview_charts(df, state.output_dir)

    if state.viz_plan.get("visualizations"):
        llm = _build_llm(temperature=0.1)
        for viz in state.viz_plan["visualizations"][:4]:
            prompt_user = (
                f"Generate Python code for this visualization:\n"
                f"Chart type: {viz.get('chart_type')}\n"
                f"Title: {viz.get('title')}\n"
                f"X column: {viz.get('x_column')}\n"
                f"Y column: {viz.get('y_column')}\n"
                f"Color column: {viz.get('color_column')}\n"
                f"Description: {viz.get('description')}\n\n"
                f"Available columns and dtypes:\n"
                f"{json.dumps([{'name': c['name'], 'dtype': c['dtype'], 'category': c.get('category')} for c in state.dataset_summary.get('columns', [])], indent=2)}\n\n"
                f"Remember: use `df` variable, save to `output_path`, call plt.close()."
            )
            try:
                response = llm.invoke(
                    [
                        SystemMessage(content=CODE_GENERATOR_PROMPT),
                        HumanMessage(content=prompt_user),
                    ]
                )
                code = response.content.strip()
                if code.startswith("```"):
                    code = code.split("```")[1]
                    if code.startswith("python"):
                        code = code[6:]
                    code = code.rsplit("```", 1)[0]

                result = execute_viz_code(code, df, state.output_dir)
                if result["success"]:
                    charts.append(
                        {
                            "id": viz.get("id", uuid.uuid4().hex[:8]),
                            "title": viz.get("title", "Chart"),
                            "path": result["path"],
                            "description": viz.get("description", ""),
                        }
                    )
                    logger.info("Chart generated: %s", viz.get("title"))
                else:
                    logger.warning("Chart failed: %s | %s", viz.get("title"), result["error"][:200])
            except Exception as e:
                logger.warning("LLM chart error: %s", e)

    state.charts = charts
    state.progress = 88
    return state


def node_write_report(state: AnalysisState) -> AnalysisState:
    if state.status == "error":
        return state

    logger.info("[node_write_report] Writing narrative report")
    state.current_step = "Writing report"
    state.progress = 90

    llm = _build_llm(temperature=0.5)
    chart_descriptions = [f"- {c['title']}: {c.get('description', '')}" for c in state.charts]
    user_msg = (
        f"Dataset profile:\n{json.dumps(state.profile, indent=2)}\n\n"
        f"Key insights:\n{json.dumps(state.insights, indent=2)}\n\n"
        f"Visualizations included:\n" + "\n".join(chart_descriptions)
    )

    try:
        response = llm.invoke(
            [SystemMessage(content=REPORT_WRITER_PROMPT), HumanMessage(content=user_msg)]
        )
        state.report_md = response.content.strip()
    except Exception as e:
        logger.warning("Report writing failed: %s", e)
        state.report_md = f"# Analysis Report\n\n{state.insights.get('executive_summary', '')}"

    state.progress = 98
    return state


def node_finalize(state: AnalysisState) -> AnalysisState:
    logger.info("[node_finalize] Analysis complete")
    state.current_step = "Complete"
    state.progress = 100
    state.status = "done"
    state.completed_at = time.time()

    parquet_path = os.path.join(state.output_dir, "_df.parquet")
    if os.path.exists(parquet_path):
        os.remove(parquet_path)

    return state


def node_handle_error(state: AnalysisState) -> AnalysisState:
    logger.error("[node_handle_error] Pipeline error: %s", state.error)
    state.status = "error"
    state.progress = 0
    return state


# ── Routing ───────────────────────────────────────────────────────────────────


def route_after_load(state: AnalysisState) -> Literal["profile", "error"]:
    return "error" if state.status == "error" else "profile"


# ── Graph Construction ────────────────────────────────────────────────────────


def build_agent() -> StateGraph:
    graph = StateGraph(AnalysisState)

    graph.add_node("load", node_load)
    graph.add_node("profile", node_profile)
    graph.add_node("insights", node_insights)
    graph.add_node("plan_viz", node_plan_viz)
    graph.add_node("generate_viz", node_generate_viz)
    graph.add_node("write_report", node_write_report)
    graph.add_node("finalize", node_finalize)
    graph.add_node("error", node_handle_error)

    graph.add_edge(START, "load")
    graph.add_conditional_edges("load", route_after_load, {"profile": "profile", "error": "error"})
    graph.add_edge("profile", "insights")
    graph.add_edge("insights", "plan_viz")
    graph.add_edge("plan_viz", "generate_viz")
    graph.add_edge("generate_viz", "write_report")
    graph.add_edge("write_report", "finalize")
    graph.add_edge("finalize", END)
    graph.add_edge("error", END)

    return graph.compile()


# ── Public API ────────────────────────────────────────────────────────────────


def run_analysis(file_path: str, output_dir: str, session_id: str | None = None) -> dict[str, Any]:
    """Run the full analysis pipeline."""
    os.makedirs(output_dir, exist_ok=True)

    initial_state = AnalysisState(
        file_path=file_path,
        output_dir=output_dir,
        session_id=session_id or uuid.uuid4().hex,
    )

    agent = build_agent()
    result = agent.invoke(initial_state)

    if isinstance(result, dict):
        return {
            "session_id": result.get("session_id", session_id),
            "status": result.get("status", "done"),
            "current_step": result.get("current_step", "Complete"),
            "progress": result.get("progress", 100),
            "error": result.get("error"),
            "profile": result.get("profile", {}),
            "insights": result.get("insights", {}),
            "charts": result.get("charts", []),
            "report_md": result.get("report_md", ""),
            "duration_s": result.get("completed_at")
            and round(result["completed_at"] - result["started_at"], 2),
        }
    return result.to_dict()
