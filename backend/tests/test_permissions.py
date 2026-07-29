"""Rollen & geteilter Arbeitsbereich — DB-freie Tests.

Deckt die zwei sicherheitsrelevanten Punkte ab:
1. `workspace_owner_id` — entscheidet, WESSEN Daten jemand sieht (Mandantengrenze!).
2. `is_destructive` — entscheidet, WAS die Rolle „mitarbeiter" nicht darf.
"""
import uuid
from types import SimpleNamespace

from app.middleware.permissions import (
    DESTRUCTIVE_POST_PATHS,
    is_destructive,
)
from app.models.user import NON_DESTRUCTIVE_ROLES, UserRole, workspace_owner_id


def _user(**over):
    base = dict(id=uuid.uuid4(), works_for_id=None, role=UserRole.user)
    base.update(over)
    return SimpleNamespace(**base)


class TestWorkspaceResolution:
    def test_normal_user_owns_their_workspace(self):
        u = _user()
        assert workspace_owner_id(u) == u.id

    def test_admin_owns_their_workspace(self):
        u = _user(role=UserRole.admin)
        assert workspace_owner_id(u) == u.id

    def test_mitarbeiter_works_in_boss_workspace(self):
        boss = _user()
        emp = _user(role=UserRole.mitarbeiter, works_for_id=boss.id)
        assert workspace_owner_id(emp) == boss.id
        assert workspace_owner_id(emp) != emp.id

    def test_falls_back_to_own_id_without_link(self):
        # Regression: ohne works_for_id darf NIE ein fremder Bereich entstehen
        emp = _user(role=UserRole.mitarbeiter, works_for_id=None)
        assert workspace_owner_id(emp) == emp.id

    def test_returns_uuid_not_none(self):
        # Ein None würde die Tenancy global entsperren (alle Mandanten sichtbar!)
        for u in (_user(), _user(works_for_id=uuid.uuid4())):
            assert isinstance(workspace_owner_id(u), uuid.UUID)


class TestRoles:
    def test_four_roles_exist(self):
        assert {r.value for r in UserRole} == {"admin", "user", "mitarbeiter", "verkaeufer"}

    def test_only_mitarbeiter_is_non_destructive(self):
        # `verkaeufer` steht bewusst NICHT hier: Löschen ist erlaubt, aber
        # umkehrbar (Papierkorb) und gedeckelt. Ein Verbot wäre die falsche
        # Antwort — Leads aussortieren ist Kernarbeit im Vertrieb.
        assert NON_DESTRUCTIVE_ROLES == {UserRole.mitarbeiter}
        assert UserRole.admin not in NON_DESTRUCTIVE_ROLES
        assert UserRole.user not in NON_DESTRUCTIVE_ROLES
        assert UserRole.verkaeufer not in NON_DESTRUCTIVE_ROLES

    def test_scoped_and_workspace_roles(self):
        from app.models.user import ROLES_REQUIRING_WORKSPACE, SCOPED_ROLES

        assert SCOPED_ROLES == {UserRole.verkaeufer}
        # Beide Rollen arbeiten IM Bereich eines anderen — ohne works_for_id
        # hätten sie einen leeren eigenen Bereich und die Rolle wäre sinnlos.
        assert ROLES_REQUIRING_WORKSPACE == {UserRole.mitarbeiter, UserRole.verkaeufer}

    def test_api_keys_and_supervision_are_owner_only(self):
        from types import SimpleNamespace

        from app.models.user import may_administer_leads, may_manage_api_keys

        for role in (UserRole.mitarbeiter, UserRole.verkaeufer):
            u = SimpleNamespace(role=role)
            assert not may_manage_api_keys(u), f"{role} darf keine Schlüssel tauschen"
            # Die Aufsicht über die eigene Arbeit wäre kein Sicherheitsnetz.
            assert not may_administer_leads(u), f"{role} darf keine Aufsicht führen"
        for role in (UserRole.admin, UserRole.user):
            u = SimpleNamespace(role=role)
            assert may_manage_api_keys(u)
            assert may_administer_leads(u)

    def test_role_value_fits_column(self):
        # Spalte ist VARCHAR(20) — längerer Wert würde beim Insert knallen
        for r in UserRole:
            assert len(r.value) <= 20


class TestIsDestructive:
    def test_every_api_delete_is_destructive(self):
        for path in (
            "/api/customers/123", "/api/rainmaker/leads/abc", "/api/invoices/x",
            "/api/todos/1", "/api/attachments/9", "/api/expenses/7",
        ):
            assert is_destructive("DELETE", path), path

    def test_merge_endpoints_are_destructive(self):
        # Merge löscht Leads per POST — ohne Denylist wäre das eine Lücke
        for path in DESTRUCTIVE_POST_PATHS:
            assert is_destructive("POST", path), path
            assert is_destructive("POST", path + "/"), path   # trailing slash

    def test_normal_writes_are_allowed(self):
        assert not is_destructive("POST", "/api/rainmaker/leads")
        assert not is_destructive("PUT", "/api/rainmaker/leads/abc")
        assert not is_destructive("PATCH", "/api/customers/abc")
        assert not is_destructive("POST", "/api/todos")
        assert not is_destructive("POST", "/api/invoices/x/credit-note")

    def test_reads_are_allowed(self):
        assert not is_destructive("GET", "/api/customers")
        assert not is_destructive("GET", "/api/rainmaker/duplicates")

    def test_non_api_delete_untouched(self):
        # z. B. statische Auslieferung — die Sperre gilt nur für die API
        assert not is_destructive("DELETE", "/assets/x.js")
