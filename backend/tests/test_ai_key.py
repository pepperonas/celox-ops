"""Tests für den KI-Zugang pro Arbeitsbereich (eigener Anthropic-Key).

Der Schlüssel lag global in der `.env` und galt für alle — ein zweiter
Bereichs-Inhaber hätte auf Kosten des ersten abgefragt. Hier ist festgenagelt,
dass die Auflösung jetzt am Arbeitsbereich hängt, dass der Schlüssel nie in einer
Antwort auftaucht und dass Mitarbeitende ihn nicht austauschen können.
"""
import pathlib
import re

from app.models.user import UserRole, may_manage_api_keys
from app.schemas.app_settings import AppSettingsResponse, AppSettingsUpdate
from app.services.ai_key import MISSING_KEY_DETAIL


class _User:
    def __init__(self, role):
        self.role = role


# --------------------------------------------------------------------------- #
#  Wer darf den Schlüssel ändern?
# --------------------------------------------------------------------------- #
class TestKeyPermission:
    def test_owner_roles_may_manage(self):
        assert may_manage_api_keys(_User(UserRole.admin)) is True
        assert may_manage_api_keys(_User(UserRole.user)) is True

    def test_mitarbeiter_may_not(self):
        """Sie nutzen den Schlüssel des Inhabers — ihn zu tauschen wäre eine
        Entscheidung über fremdes Geld."""
        assert may_manage_api_keys(_User(UserRole.mitarbeiter)) is False

    def test_unknown_object_is_treated_as_allowed_owner(self):
        # Kein role-Attribut (z. B. Bootstrap/Skript) → nicht als Mitarbeitende(r).
        assert may_manage_api_keys(object()) is True


# --------------------------------------------------------------------------- #
#  Der Schlüssel darf NIE zurückgegeben werden
# --------------------------------------------------------------------------- #
class TestNoLeak:
    def test_response_schema_has_no_key_field(self):
        fields = set(AppSettingsResponse.model_fields)
        assert "anthropic_api_key" not in fields
        assert "google_places_api_key" not in fields
        # Nur Zustand + Maske gehen nach draußen.
        assert {"ai_key_configured", "ai_key_hint"} <= fields

    def test_update_schema_accepts_the_key(self):
        upd = AppSettingsUpdate(anthropic_api_key="sk-ant-test")
        assert upd.anthropic_api_key == "sk-ant-test"
        # "" ist die dokumentierte Löschgeste, None heißt „unverändert".
        assert AppSettingsUpdate(anthropic_api_key="").anthropic_api_key == ""
        assert AppSettingsUpdate().anthropic_api_key is None

    def test_router_masks_instead_of_returning(self):
        source = (pathlib.Path(__file__).resolve().parent.parent
                  / "app" / "routers" / "settings.py").read_text()
        assert "ai_key_hint=mask_key(row.anthropic_api_key)" in source
        assert "ai_key_configured=bool(row.anthropic_api_key)" in source


# --------------------------------------------------------------------------- #
#  Kein globaler .env-Rückfall zur Laufzeit
# --------------------------------------------------------------------------- #
class TestNoGlobalFallback:
    def test_runtime_code_does_not_read_the_env_key(self):
        """Ein stiller Rückfall auf die `.env` würde bedeuten: neuer Nutzer ohne
        eigenen Schlüssel fragt auf Kosten des `.env`-Inhabers ab. Erlaubt ist der
        Zugriff nur in `config.py` (Definition) und im Übernahme-Skript."""
        root = pathlib.Path(__file__).resolve().parent.parent / "app"
        allowed = {"config.py", "adopt_env_anthropic_key.py"}
        offenders = []
        for path in root.rglob("*.py"):
            if path.name in allowed:
                continue
            for line in path.read_text().splitlines():
                if re.search(r"settings\.ANTHROPIC_API_KEY", line):
                    offenders.append(f"{path.relative_to(root)}: {line.strip()}")
        assert not offenders, "Globaler Key-Zugriff gefunden:\n" + "\n".join(offenders)

    def test_missing_key_message_points_to_the_settings(self):
        """Der 503 muss handlungsfähig machen, nicht nur meckern."""
        assert "Einstellungen" in MISSING_KEY_DETAIL
        assert "console.anthropic.com" in MISSING_KEY_DETAIL
        assert ".env" not in MISSING_KEY_DETAIL, \
            "Nutzer haben keinen Zugriff auf die .env — der Hinweis wäre nutzlos"


# --------------------------------------------------------------------------- #
#  Übernahme-Skript
# --------------------------------------------------------------------------- #
class TestAdoptScript:
    def test_never_prints_the_key_in_clear_text(self):
        source = (pathlib.Path(__file__).resolve().parent.parent
                  / "app" / "scripts" / "adopt_env_anthropic_key.py").read_text()
        # Jede Ausgabe, die den Schlüssel erwähnt, MUSS ihn maskieren.
        assert "mask_key(env_key)" in source
        unmasked = [ln.strip() for ln in source.splitlines()
                    if "print(" in ln and "env_key" in ln and "mask_key" not in ln]
        assert not unmasked, ("Schlüssel im Klartext ausgegeben:\n" + "\n".join(unmasked))

    def test_refuses_mitarbeiter_and_defaults_to_dry_run(self):
        source = (pathlib.Path(__file__).resolve().parent.parent
                  / "app" / "scripts" / "adopt_env_anthropic_key.py").read_text()
        assert "works_for_id is not None" in source
        assert 'action="store_true"' in source and "Trockenlauf" in source
