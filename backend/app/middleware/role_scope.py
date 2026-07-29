"""Erlaubnisliste für zugeschnittene Rollen (aktuell `verkaeufer`).

**Deny-by-default.** Das übrige Rechtemodell dieser App arbeitet mit Verboten:
`require_admin` auf einzelnen Routern, die Löschsperre in
`middleware/permissions.py`. Für eine Rolle, die NUR einen Ausschnitt sehen darf,
ist das die falsche Richtung — sie wäre standardmäßig überall drin (Kunden,
Rechnungen, Ausgaben, EÜR, Einstellungen), und jede künftig hinzugefügte Route
wäre ein neues Leck.

Deshalb hier umgekehrt: Was nicht ausdrücklich erlaubt ist, wird abgelehnt. Eine
neue Route ist damit im Zweifel gesperrt, nicht offen.

Der Zuschnitt für `verkaeufer`:
- **Pipeline (Leads + Aktivitäten):** lesen, anlegen, ändern, löschen. Löschen
  wirkt als Papierkorb und ist pro Tag gedeckelt (s. `rainmaker.py`).
- **Akquise-Vorlagen:** nur lesen und kopieren (der Kopierzähler ist die einzige
  erlaubte Schreiboperation dort — er ändert keinen Inhalt).
- **Eigenes Konto:** Passwort, 2FA.
- **Gesperrt:** E-Mail-Versand, alle kostenpflichtigen KI-Funktionen, Massen-
  Importe, Zusammenführen, Rainmaker-Auswertungen/Ziele/Einstellungen, der
  Papierkorb selbst (Aufsicht liegt beim Inhaber) — und der gesamte Rest der App.
"""
import re

# Jede Regel: (Methoden, kompiliertes Pfadmuster). Muster matchen den GANZEN Pfad
# (`fullmatch`), damit ein Präfix nicht versehentlich mehr freigibt als gemeint —
# `/api/rainmaker/leads` darf nicht `/api/rainmaker/leads/{id}/send-email`
# mitfreigeben.
_UUID = r"[0-9a-fA-F-]{36}"

_VERKAEUFER_RULES: list[tuple[frozenset[str], re.Pattern[str]]] = [
    # --- Pipeline: Leads ---
    (frozenset({"GET"}), re.compile(r"/api/rainmaker/leads")),
    (frozenset({"POST"}), re.compile(r"/api/rainmaker/leads")),
    (frozenset({"GET", "PUT", "DELETE"}), re.compile(rf"/api/rainmaker/leads/{_UUID}")),
    # Einzelprüfung einer E-Mail-Adresse (DNS/MX, kostenlos). Die Sammelprüfung
    # `/leads/verify-emails` bleibt gesperrt: Massenschreibvorgang.
    (frozenset({"POST"}), re.compile(rf"/api/rainmaker/leads/{_UUID}/verify-email")),
    # Website-Befunde nur ANSEHEN. Das Auslösen einer Analyse bleibt gesperrt
    # (die Tiefenanalyse kostet Geld, und die schnelle läuft ohnehin automatisch).
    (frozenset({"GET"}), re.compile(rf"/api/rainmaker/leads/{_UUID}/website-analys(is|es)")),
    # --- Pipeline: Aktivitäten (der „nächste Schritt" ist Kernarbeit) ---
    (frozenset({"GET"}), re.compile(rf"/api/rainmaker/leads/{_UUID}/activities")),
    (frozenset({"POST"}), re.compile(rf"/api/rainmaker/leads/{_UUID}/activities")),
    (frozenset({"POST"}), re.compile(rf"/api/rainmaker/activities/{_UUID}/complete")),
    (frozenset({"DELETE"}), re.compile(rf"/api/rainmaker/activities/{_UUID}")),
    # --- Pipeline: Kontext ---
    (frozenset({"GET"}), re.compile(r"/api/rainmaker/ping")),
    # Nur der Zählerstand für die „N Websites in Analyse"-Pille. Das Anstoßen
    # (`/analysis-queue/enqueue-missing`) ist nicht dabei.
    (frozenset({"GET"}), re.compile(r"/api/rainmaker/analysis-queue")),
    # Nachrichten-Vorlagen am Lead (Betreff/Text für mailto bzw. Zwischenablage).
    (frozenset({"GET"}), re.compile(r"/api/rainmaker/templates")),
    # Autocomplete für Lead-Felder (Funktion, Quelle, Tags, Target).
    (frozenset({"GET"}), re.compile(r"/api/suggestions")),
    # --- Akquise-Vorlagen: lesen + kopieren ---
    (frozenset({"GET"}), re.compile(r"/api/outreach/templates")),
    (frozenset({"POST"}), re.compile(rf"/api/outreach/templates/{_UUID}/copied")),
    # --- Eigenes Konto ---
    (frozenset({"GET"}), re.compile(r"/api/auth/me")),
    (frozenset({"GET"}), re.compile(r"/api/auth/info")),
    (frozenset({"GET", "POST"}), re.compile(r"/api/auth/2fa/(init|enable|disable)")),
    (frozenset({"POST"}), re.compile(r"/api/users/me/password")),
    (frozenset({"GET"}), re.compile(r"/api/health")),
]

RULES: dict[str, list[tuple[frozenset[str], re.Pattern[str]]]] = {
    "verkaeufer": _VERKAEUFER_RULES,
}

DENY_MESSAGE = (
    "Diese Ansicht gehört nicht zum Zugriff der Rolle „Verkäufer“ — "
    "erlaubt sind die Pipeline und die Akquise-Vorlagen."
)


def is_scoped(role: str | None) -> bool:
    """Unterliegt diese Rolle einer Erlaubnisliste?"""
    return (role or "") in RULES


def allowed_for_role(role: str | None, method: str, path: str) -> bool:
    """Rein + testbar: Darf diese Rolle diesen Request stellen?

    Unbekannte/nicht zugeschnittene Rollen sind hier immer erlaubt — für sie
    gelten die übrigen Regeln (`require_admin`, Löschsperre). Nur die in `RULES`
    genannten Rollen werden eingeschränkt.
    """
    rules = RULES.get(role or "")
    if rules is None:
        return True
    # Abschließender Schrägstrich ist bedeutungslos; ein leerer Pfad nicht.
    clean = path.rstrip("/") or "/"
    return any(method in methods and pattern.fullmatch(clean) for methods, pattern in rules)
