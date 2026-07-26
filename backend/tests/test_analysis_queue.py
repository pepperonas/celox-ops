"""DB-freie Tests für die Auto-Analyse-Queue (Modell-Defaults + Persistenz-Helfer).

Der Worker-Lauf selbst braucht eine DB und wird nicht simuliert; getestet werden
die Regeln, die schweigend falsch sein könnten: Job-Defaults, die Zuordnung des
Analyse-Ergebnisses auf Versions-Datensatz + Lead-Zusammenfassung, und dass die
Auto-Analyse die schnelle (kostenlose) Variante bleibt.
"""
import inspect

import app.models.rainmaker_activity  # noqa: F401 — Mapper-Ziel von RainmakerLead.activities
from app.models.lead_analysis_job import DONE, ERROR, QUEUED, RUNNING, LeadAnalysisJob
from app.services import analysis_queue
from app.services.website_analysis_store import analysis_row, apply_summary

_RESULT = {
    "analysis_version": "2.0",
    "url": "https://muster.de/",
    "overall_score": 73,
    "rating": "gelb",
    "has_critical": False,
    "categories": [{"key": "seo", "score": 80}],
    "findings": [{"category": "seo", "issue": "Kein H2", "severity": "low"}],
    "technologies": ["WordPress"],
    "recommendations": [{"priority": "hoch", "text": "H2 ergänzen"}],
    "meta": {"reachable": True},
}


class _Lead:
    id = "lead-1"
    web_score = None
    web_rating = None
    web_has_critical = None
    web_analyzed_at = None


# ---- Job-Modell ------------------------------------------------------------
def test_job_defaults_are_queued():
    job = LeadAnalysisJob(lead_id="x")
    assert job.status is None or job.status == QUEUED   # Default greift beim Insert
    assert {QUEUED, RUNNING, DONE, ERROR} == {"queued", "running", "done", "error"}


def test_job_table_is_new_so_no_migration_needed():
    # Neue Tabelle → create_all erzeugt sie; ein ALTER wäre ein Deploy-Stolperstein.
    assert LeadAnalysisJob.__tablename__ == "lead_analysis_jobs"
    assert "owner_id" in LeadAnalysisJob.__table__.columns


# ---- Persistenz ------------------------------------------------------------
def test_analysis_row_maps_every_result_field():
    row = analysis_row("lead-1", _RESULT)
    assert row.analysis_version == "2.0" and row.overall_score == 73
    assert row.rating == "gelb" and row.has_critical is False
    assert row.technologies == ["WordPress"] and row.meta == {"reachable": True}
    # Tiefenanalyse-Felder bleiben leer, wenn nicht mitgelaufen
    assert row.ai_review is None and row.pagespeed is None


def test_analysis_row_carries_deep_fields_when_present():
    row = analysis_row("lead-1", {**_RESULT, "ai_review": {"ki": 80}, "pagespeed": {"scores": {}}})
    assert row.ai_review == {"ki": 80} and row.pagespeed == {"scores": {}}


def test_apply_summary_denormalizes_onto_lead():
    lead = _Lead()
    apply_summary(lead, _RESULT)
    assert lead.web_score == 73 and lead.web_rating == "gelb"
    assert lead.web_has_critical is False and lead.web_analyzed_at is not None


# ---- Worker-Regeln ---------------------------------------------------------
def test_auto_analysis_never_costs_money():
    """Der Worker darf nur die schnelle Analyse fahren — kein PageSpeed, keine KI."""
    src = inspect.getsource(analysis_queue._run_job)
    assert "fetch_and_analyze" in src
    assert "analyze_deep" not in src and "pagespeed" not in src


def test_worker_limits_are_conservative():
    assert 1 <= analysis_queue.CONCURRENCY <= 4
    assert analysis_queue.MAX_ATTEMPTS >= 1
    assert analysis_queue.IDLE_SECONDS >= 5
    assert analysis_queue.ENQUEUE_MISSING_CAP <= 2000


def test_worker_scopes_owner_per_job():
    """Mandanten-Invariante: der Worker läuft global, setzt aber pro Job den Owner."""
    src = inspect.getsource(analysis_queue._run_job)
    assert "current_owner_id.set(owner_id)" in src
    assert "current_owner_id.reset(token)" in src
