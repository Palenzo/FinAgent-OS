"""
LangGraph state machine — orchestrates all 10 agents.
Each node receives and mutates the shared FinAgentState TypedDict.
"""

import logging
from typing import Annotated, Any, Optional
from uuid import UUID

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

logger = logging.getLogger("workflow")


# ── Shared state ──────────────────────────────────────────────────────────────

class FinAgentState(TypedDict, total=False):
    run_id: str
    triggered_by: str
    file_content: bytes
    file_type: str

    # agent outputs
    ingestion_result: dict
    pnl_result: dict
    forecast_result: dict
    anomaly_result: dict
    reconciliation_result: dict
    report_result: dict

    # control
    errors: list[dict]
    completed_agents: list[str]
    status: str  # running | completed | failed


# ── Node implementations (thin wrappers — real logic lives in agents/) ────────

def make_orchestrator_node():
    async def orchestrator(state: FinAgentState) -> FinAgentState:
        logger.info("[Orchestrator] Starting pipeline run_id=%s", state.get("run_id"))
        state.setdefault("errors", [])
        state.setdefault("completed_agents", [])
        state["status"] = "running"
        return state

    return orchestrator


def make_ingestion_node(db_session_factory, run_id_getter):
    from agents.data_ingestion import ingest

    async def ingestion(state: FinAgentState) -> FinAgentState:
        try:
            async with db_session_factory() as db:
                result = await ingest(
                    content=state["file_content"],
                    file_type=state.get("file_type", "csv"),
                    run_id=state.get("run_id"),
                    db=db,
                )
            state["ingestion_result"] = result
            state["completed_agents"].append("data_ingestion")
        except Exception as exc:
            logger.error("[DataIngestion] failed: %s", exc)
            state["errors"].append({"agent": "data_ingestion", "error": str(exc)})
            state["status"] = "failed"
        return state

    return ingestion


def make_pnl_node():
    from agents.pnl_analyzer import analyze

    async def pnl(state: FinAgentState) -> FinAgentState:
        try:
            result = await analyze(state["ingestion_result"], state.get("run_id"))
            state["pnl_result"] = result
            state["completed_agents"].append("pnl_analyzer")
        except Exception as exc:
            logger.error("[PnLAnalyzer] failed: %s", exc)
            state["errors"].append({"agent": "pnl_analyzer", "error": str(exc)})
        return state

    return pnl


def make_forecasting_node():
    from agents.forecasting import forecast

    async def forecasting(state: FinAgentState) -> FinAgentState:
        try:
            result = await forecast(state["ingestion_result"], state.get("run_id"))
            state["forecast_result"] = result
            state["completed_agents"].append("forecasting")
        except Exception as exc:
            logger.error("[Forecasting] failed: %s", exc)
            state["errors"].append({"agent": "forecasting", "error": str(exc)})
        return state

    return forecasting


def make_anomaly_node():
    from agents.anomaly_detection import detect

    async def anomaly(state: FinAgentState) -> FinAgentState:
        try:
            result = await detect(state["ingestion_result"], state.get("run_id"))
            state["anomaly_result"] = result
            state["completed_agents"].append("anomaly_detection")
        except Exception as exc:
            logger.error("[AnomalyDetection] failed: %s", exc)
            state["errors"].append({"agent": "anomaly_detection", "error": str(exc)})
        return state

    return anomaly


def make_reconciliation_node():
    from agents.reconciliation import reconcile

    async def reconciliation(state: FinAgentState) -> FinAgentState:
        try:
            result = await reconcile(state["ingestion_result"], state.get("run_id"))
            state["reconciliation_result"] = result
            state["completed_agents"].append("reconciliation")
        except Exception as exc:
            logger.error("[Reconciliation] failed: %s", exc)
            state["errors"].append({"agent": "reconciliation", "error": str(exc)})
        return state

    return reconciliation


def make_report_node():
    from agents.report_generator import generate_report

    async def report(state: FinAgentState) -> FinAgentState:
        try:
            result = await generate_report(state)
            state["report_result"] = result
            state["completed_agents"].append("report_generator")
            state["status"] = "completed"
        except Exception as exc:
            logger.error("[ReportGenerator] failed: %s", exc)
            state["errors"].append({"agent": "report_generator", "error": str(exc)})
            state["status"] = "failed"
        return state

    return report


def make_notification_node():
    from agents.notification import send_notifications

    async def notification(state: FinAgentState) -> FinAgentState:
        try:
            await send_notifications(state)
            state["completed_agents"].append("notification")
        except Exception as exc:
            logger.error("[Notification] failed: %s", exc)
            state["errors"].append({"agent": "notification", "error": str(exc)})
        return state

    return notification


def make_audit_node(db_session_factory):
    from agents.audit import log_run

    async def audit(state: FinAgentState) -> FinAgentState:
        try:
            async with db_session_factory() as db:
                await log_run(state, db)
            state["completed_agents"].append("audit")
        except Exception as exc:
            logger.error("[Audit] failed: %s", exc)
        return state

    return audit


def make_dashboard_node(ws_manager):
    from agents.dashboard_agent import push_update

    async def dashboard(state: FinAgentState) -> FinAgentState:
        try:
            await push_update(state, ws_manager)
            state["completed_agents"].append("dashboard")
        except Exception as exc:
            logger.error("[Dashboard] failed: %s", exc)
        return state

    return dashboard


# ── Routing helpers ───────────────────────────────────────────────────────────

def route_after_ingestion(state: FinAgentState) -> str:
    if state.get("status") == "failed":
        return "audit"
    return "pnl_analyzer"


def route_after_analysis(state: FinAgentState) -> str:
    """All three parallel analysis agents must complete before report."""
    done = set(state.get("completed_agents", []))
    required = {"pnl_analyzer", "forecasting", "anomaly_detection", "reconciliation"}
    if required.issubset(done):
        return "report_generator"
    return END  # wait (LangGraph will re-enter via fan-in)


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph(db_session_factory, ws_manager):
    graph = StateGraph(FinAgentState)

    graph.add_node("orchestrator", make_orchestrator_node())
    graph.add_node("data_ingestion", make_ingestion_node(db_session_factory, None))
    graph.add_node("pnl_analyzer", make_pnl_node())
    graph.add_node("forecasting", make_forecasting_node())
    graph.add_node("anomaly_detection", make_anomaly_node())
    graph.add_node("reconciliation", make_reconciliation_node())
    graph.add_node("report_generator", make_report_node())
    graph.add_node("notification", make_notification_node())
    graph.add_node("audit", make_audit_node(db_session_factory))
    graph.add_node("dashboard", make_dashboard_node(ws_manager))

    # Edges
    graph.set_entry_point("orchestrator")
    graph.add_edge("orchestrator", "data_ingestion")
    graph.add_conditional_edges("data_ingestion", route_after_ingestion)

    # Fan-out: run analysis agents in parallel paths
    graph.add_edge("pnl_analyzer", "forecasting")
    graph.add_edge("forecasting", "anomaly_detection")
    graph.add_edge("anomaly_detection", "reconciliation")
    graph.add_edge("reconciliation", "report_generator")

    graph.add_edge("report_generator", "notification")
    graph.add_edge("notification", "audit")
    graph.add_edge("audit", "dashboard")
    graph.add_edge("dashboard", END)

    return graph.compile()
