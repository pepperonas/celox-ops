"""Unit tests for the C1 commit-summary grouping (routers/github._commit_theme).
Pure logic, no DB / no network. Run with the smoke tests in-container."""
from app.routers.github import _MAINT_LABEL, _NOISE_THEMES, _commit_theme


def test_prefix_before_colon_is_the_theme():
    assert _commit_theme("Rechnung: KI-Import bis Rechnungsdatum") == "Rechnung"
    assert _commit_theme("Dashboard: Toggles persistent") == "Dashboard"


def test_phase_suffix_stripped():
    assert _commit_theme("Multi-User Phase 2: Daten-Isolation") == "Multi-User"
    assert _commit_theme("Multi-User Phase 3: Nutzerverwaltung") == "Multi-User"


def test_trailing_parenthetical_stripped():
    # "Perf (Paket 2)" → strip "(Paket 2)" → "Perf" → maintenance bucket
    assert _commit_theme("Perf (Paket 2): schneller") == _MAINT_LABEL
    assert _commit_theme("Feature (WIP): x") == "Feature"


def test_version_suffix_stripped():
    assert _commit_theme("Release v1.2.0: notes") == "Release"
    assert _commit_theme("Bump 2.0: deps") == "Bump"


def test_noise_prefixes_fold_to_maintenance():
    for p in ["Fix", "Docs", "Doku", "Tests", "Chore", "Refactor", "Perf", "CI", "Build", "Style"]:
        assert _commit_theme(f"{p}: irgendwas") == _MAINT_LABEL, p


def test_noise_is_case_insensitive():
    assert _commit_theme("FIX: x") == _MAINT_LABEL
    assert _commit_theme("docs: x") == _MAINT_LABEL


def test_subject_without_colon_kept_verbatim():
    assert _commit_theme("Tighten vertical spacing on /flyer/") == "Tighten vertical spacing on /flyer/"


def test_theme_truncated_to_60_chars():
    long = "X" * 100  # no colon, no paren, no version
    assert len(_commit_theme(long)) == 60


def test_whitespace_around_prefix_trimmed():
    assert _commit_theme("Frontend : Motion-Pass") == "Frontend"
    assert _commit_theme("  Kunden: Detailansicht") == "Kunden"


def test_non_noise_prefix_preserves_casing():
    assert _commit_theme("RECHNUNG: x") == "RECHNUNG"


def test_maint_label_and_noise_set_shape():
    assert _MAINT_LABEL and isinstance(_MAINT_LABEL, str)
    # a representative subset must be present
    assert {"fix", "docs", "doku", "tests", "chore", "perf"} <= _NOISE_THEMES
