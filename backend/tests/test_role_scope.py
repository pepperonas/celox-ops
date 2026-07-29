"""Erlaubnisliste der Rolle „Verkäufer" — deny-by-default.

Der wichtigste Test ist der negative: Was NICHT auf der Liste steht, muss
abgelehnt werden. Ein Test, der nur die erlaubten Pfade prüft, würde eine zu
weite Regel (z. B. ein Präfix-Match) nicht bemerken.
"""
import pytest

from app.middleware.role_scope import RULES, allowed_for_role, is_scoped

LEAD = "/api/rainmaker/leads/11111111-2222-3333-4444-555555555555"
ACT = "/api/rainmaker/activities/11111111-2222-3333-4444-555555555555"
TPL = "/api/outreach/templates/11111111-2222-3333-4444-555555555555"


class TestUnscopedRolesAreUntouched:
    @pytest.mark.parametrize("role", ["admin", "user", "mitarbeiter", None, "", "unbekannt"])
    def test_everything_allowed(self, role):
        # Für sie gelten die anderen Regeln (require_admin, Löschsperre) — diese
        # Middleware darf sie nicht zusätzlich einschränken.
        assert allowed_for_role(role, "DELETE", "/api/invoices/x")
        assert allowed_for_role(role, "GET", "/api/euer")
        assert not is_scoped(role)

    def test_verkaeufer_is_scoped(self):
        assert is_scoped("verkaeufer")
        assert "verkaeufer" in RULES


class TestPipelineIsAllowed:
    @pytest.mark.parametrize("method,path", [
        ("GET", "/api/rainmaker/leads"),
        ("POST", "/api/rainmaker/leads"),
        ("GET", LEAD),
        ("PUT", LEAD),
        ("DELETE", LEAD),
        ("POST", f"{LEAD}/verify-email"),
        ("GET", f"{LEAD}/activities"),
        ("POST", f"{LEAD}/activities"),
        ("POST", f"{ACT}/complete"),
        ("DELETE", ACT),
        ("GET", f"{LEAD}/website-analysis"),
        ("GET", f"{LEAD}/website-analyses"),
        ("GET", "/api/rainmaker/ping"),
        ("GET", "/api/rainmaker/analysis-queue"),
        ("GET", "/api/rainmaker/templates"),
        ("GET", "/api/suggestions"),
    ])
    def test_allowed(self, method, path):
        assert allowed_for_role("verkaeufer", method, path)

    def test_trailing_slash_is_irrelevant(self):
        assert allowed_for_role("verkaeufer", "GET", "/api/rainmaker/leads/")


class TestOutreachIsReadOnly:
    def test_read_and_copy_counter_allowed(self):
        assert allowed_for_role("verkaeufer", "GET", "/api/outreach/templates")
        assert allowed_for_role("verkaeufer", "POST", f"{TPL}/copied")

    @pytest.mark.parametrize("method,path", [
        ("POST", "/api/outreach/templates"),
        ("PUT", TPL),
        ("DELETE", TPL),
        ("POST", "/api/outreach/templates/seed"),
    ])
    def test_writing_templates_denied(self, method, path):
        assert not allowed_for_role("verkaeufer", method, path)


class TestEmailAndPaidAiDenied:
    @pytest.mark.parametrize("path", [
        f"{LEAD}/send-email",            # Kernanforderung: kein Versand
        f"{LEAD}/draft-email",           # KI-Entwurf kostet Geld des Inhabers
        f"{LEAD}/analyze-website",       # Tiefenanalyse kostet Geld
        f"{LEAD}/chat-import/preview",   # Vision-Lauf kostet Geld
        "/api/rainmaker/leads/intake",
        "/api/rainmaker/discover/ai/preview",
        "/api/rainmaker/discover/preview",
        "/api/rainmaker/discover/import",
        "/api/rainmaker/import/linkedin",
        "/api/rainmaker/duplicates/merge",
        "/api/rainmaker/duplicates/merge-batch",
        "/api/rainmaker/leads/verify-emails",
        "/api/rainmaker/analysis-queue/enqueue-missing",
    ])
    def test_denied(self, path):
        assert not allowed_for_role("verkaeufer", "POST", path)


class TestSupervisionIsOwnerOnly:
    """Papierkorb und Änderungsprotokoll dürfen für die überwachte Rolle nicht
    erreichbar sein — sonst wäre der Papierkorb bloß ein Zwischenschritt."""

    @pytest.mark.parametrize("method,path", [
        ("GET", "/api/rainmaker/leads/trash"),
        ("POST", f"{LEAD}/restore"),
        ("DELETE", f"{LEAD}/purge"),
        ("GET", "/api/rainmaker/lead-changes"),
        ("POST", "/api/rainmaker/lead-changes/11111111-2222-3333-4444-555555555555/revert"),
    ])
    def test_denied(self, method, path):
        assert not allowed_for_role("verkaeufer", method, path)

    def test_trash_is_not_swallowed_by_the_leads_rule(self):
        # `/leads` ist erlaubt — `fullmatch` verhindert, dass damit auch
        # `/leads/trash` freigegeben wird. Genau dieser Fehler wäre bei einem
        # Präfix-Match unsichtbar geblieben.
        assert allowed_for_role("verkaeufer", "GET", "/api/rainmaker/leads")
        assert not allowed_for_role("verkaeufer", "GET", "/api/rainmaker/leads/trash")


class TestRestOfAppDenied:
    @pytest.mark.parametrize("method,path", [
        ("GET", "/api/customers"),
        ("POST", "/api/customers"),
        ("GET", "/api/invoices"),
        ("GET", "/api/expenses"),
        ("GET", "/api/contracts"),
        ("GET", "/api/orders"),
        ("GET", "/api/euer"),
        ("GET", "/api/time-entries"),
        ("GET", "/api/todos"),
        ("GET", "/api/dashboard/stats"),
        ("GET", "/api/documents/templates"),
        ("GET", "/api/compliance/overview"),
        ("GET", "/api/search"),
        ("GET", "/api/settings"),
        ("PUT", "/api/settings"),
        ("GET", "/api/users"),
        ("GET", "/api/backup/export"),
        ("GET", "/api/ical"),
        ("GET", "/api/rainmaker/today"),
        ("GET", "/api/rainmaker/stats"),
        ("GET", "/api/rainmaker/dream"),
        ("GET", "/api/rainmaker/settings"),
        ("GET", "/api/rainmaker/goals"),
        ("GET", "/api/rainmaker/duplicates"),
        ("GET", "/api/rainmaker/ai/usage"),
        ("GET", "/api/attachments"),
        ("GET", "/api/pagespeed/results"),
    ])
    def test_denied(self, method, path):
        assert not allowed_for_role("verkaeufer", method, path)


class TestOwnAccount:
    @pytest.mark.parametrize("method,path", [
        ("GET", "/api/auth/me"),
        ("GET", "/api/auth/2fa/init"),
        ("POST", "/api/auth/2fa/enable"),
        ("POST", "/api/auth/2fa/disable"),
        ("POST", "/api/users/me/password"),
    ])
    def test_allowed(self, method, path):
        assert allowed_for_role("verkaeufer", method, path)

    def test_other_users_untouchable(self):
        other = "/api/users/11111111-2222-3333-4444-555555555555"
        assert not allowed_for_role("verkaeufer", "PATCH", other)
        assert not allowed_for_role("verkaeufer", "DELETE", other)


class TestMethodIsPartOfTheRule:
    def test_read_only_paths_reject_writes(self):
        assert allowed_for_role("verkaeufer", "GET", "/api/rainmaker/templates")
        for method in ("POST", "PUT", "DELETE", "PATCH"):
            assert not allowed_for_role("verkaeufer", method, "/api/rainmaker/templates")
