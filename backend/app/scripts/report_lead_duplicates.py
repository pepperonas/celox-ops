"""Bestandsdaten-Report: findet Verdachts-Duplikate in `rainmaker_leads`.

**Nur Report — löscht/merged nichts.** Gibt pro Owner Gruppen aus, die sich
einen normalisierten Schlüssel teilen, plus einen Behalten-Vorschlag (ältester,
bzw. bei Gleichstand der vollständigste Datensatz). Firmenname-Kollisionen
werden bewusst NUR als Warnung gelistet (verschiedene Personen teilen sich
denselben Arbeitgeber — kein Auto-Merge!).

Ausführen im Backend-Container (owner-übergreifend, ContextVar ungesetzt ⇒ global):
    docker compose -f docker-compose.dev.yml run --rm backend \
        python -m app.scripts.report_lead_duplicates
    # oder in Produktion:
    docker compose exec backend python -m app.scripts.report_lead_duplicates
"""
import asyncio
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select

from app.database import async_session_factory
# RainmakerActivity muss mit-registriert sein, sonst kann der Mapper die
# String-Relationship auf RainmakerLead nicht auflösen (Standalone-Script).
from app.models.rainmaker_activity import RainmakerActivity  # noqa: F401
from app.models.rainmaker_lead import RainmakerLead
from app.services.lead_dedup import norm_company, norm_email, norm_website

_MAX_DT = datetime.max.replace(tzinfo=timezone.utc)


def _completeness(lead: RainmakerLead) -> int:
    """Wie „vollständig" ist ein Lead — für den Behalten-Vorschlag bei Gleichstand."""
    return sum(bool(getattr(lead, f)) for f in
               ("email", "website", "phone", "address", "contact_name", "role", "notes"))


def _pick_keep(group: list[RainmakerLead]) -> RainmakerLead:
    """Behalten: ältester Datensatz; bei gleichem Alter der vollständigste."""
    return min(group, key=lambda le: (le.created_at or _MAX_DT, -_completeness(le)))


def _report(title: str, groups: dict, key_label: str, *, warning: bool = False) -> int:
    dup = {k: v for k, v in groups.items() if len(v) > 1}
    extra = sum(len(v) - 1 for v in dup.values())
    flag = "⚠ WARNUNG (keine Auto-Duplikate!) " if warning else ""
    print(f"\n=== {flag}{title}: {len(dup)} Gruppen, {extra} überzählige Datensätze ===")
    for (_owner, key), group in sorted(dup.items(), key=lambda kv: -len(kv[1]))[:40]:
        keep = _pick_keep(group)
        others = [str(le.id) for le in group if le is not keep]
        print(f"  [{key_label}={key!r}] {len(group)}× | behalten: „{keep.company}“ "
              f"({keep.id}) | prüfen: {', '.join(others)}")
    if len(dup) > 40:
        print(f"  … und {len(dup) - 40} weitere Gruppen.")
    return extra


async def main() -> None:
    async with async_session_factory() as db:
        leads = list((await db.execute(select(RainmakerLead))).scalars().all())

    by_email: dict = defaultdict(list)
    by_web: dict = defaultdict(list)
    by_comp: dict = defaultdict(list)
    for le in leads:
        if e := norm_email(le.email):
            by_email[(le.owner_id, e)].append(le)
        if w := norm_website(le.website):
            by_web[(le.owner_id, w)].append(le)
        if c := norm_company(le.company):
            by_comp[(le.owner_id, c)].append(le)

    print(f"rainmaker_leads gesamt: {len(leads)}")
    e1 = _report("Exakte E-Mail-Duplikate", by_email, "email")
    e2 = _report("Exakte Website-Duplikate", by_web, "website")
    _report("Firmenname-Kollisionen", by_comp, "company", warning=True)

    print(f"\n>>> Harte Duplikate (E-Mail/Website): {e1 + e2} überzählige Datensätze.")
    print(">>> Firmenname-Kollisionen sind NUR Hinweise — bitte manuell prüfen, "
          "NICHTS automatisch löschen.")


if __name__ == "__main__":
    asyncio.run(main())
