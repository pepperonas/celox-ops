"""Duplikat-Finder für die Bereinigung (find + merge).

Reine, netzfrei testbare Bausteine:
- **Clustering** über den normalisierten Firmennamen (exakt) PLUS Fuzzy-Kanten
  via **Trigramm-Jaccard-Ähnlichkeit** (dieselbe Idee wie `pg_trgm.similarity`,
  aber ohne DB-Extension → voll unit-testbar). Union-Find fasst zusammen.
- **Scoring nach Duplikat-Typ**, damit man keine Kollegen löscht: gleiche Firma
  + gleicher Ansprechpartner = dieselbe Person (hoch); gleiche Firma ohne
  Ansprechpartner = Firma doppelt (hoch); gleiche Firma + verschiedene
  Ansprechpartner = wahrscheinlich Kollegen (niedrig, NICHT vorausgewählt).

`find_groups()` bekommt Leads als schlichte Dicts (mind. `id`, `company`,
`contact_name`) und ist damit ohne DB/ORM testbar.
"""
import re

from app.services.lead_dedup import norm_company, norm_name

FUZZY_THRESHOLD = 0.6

# Duplikat-Typen (Grund) — steuern Score + UI-Kennzeichnung/Vorauswahl.
REASON_SAME_PERSON = "same_person"     # gleiche Firma + gleicher Ansprechpartner
REASON_FIRM = "firm"                   # gleiche Firma, beide ohne Ansprechpartner
REASON_COLLEAGUES = "colleagues"       # gleiche Firma, verschiedene Ansprechpartner
REASON_FUZZY = "fuzzy"                 # nur ähnlicher Name (kein exakter Match)


def _trigrams(value: str) -> set[str]:
    """Padded Zeichen-Trigramme (pg_trgm-artig)."""
    s = re.sub(r"\s+", " ", (value or "").strip().lower())
    if not s:
        return set()
    padded = f"  {s} "
    return {padded[i:i + 3] for i in range(len(padded) - 2)}


def trigram_similarity(a: str, b: str) -> float:
    """Jaccard-Ähnlichkeit über Trigramme, 0..1."""
    ta, tb = _trigrams(a), _trigrams(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def score_group(members: list[dict]) -> tuple[float, str]:
    """Konfidenz (0..1) + Grund für eine Kandidatengruppe."""
    exact = len({norm_company(m.get("company")) for m in members}) == 1
    names = [norm_name(m.get("contact_name")) for m in members]
    filled = [n for n in names if n]

    if len(filled) != len(set(filled)) and filled:
        score, reason = 0.95, REASON_SAME_PERSON       # gleicher Name ≥2× → dieselbe Person
    elif not filled:
        score, reason = 0.80, REASON_FIRM              # beide ohne Ansprechpartner → Firma doppelt
    else:
        score, reason = 0.30, REASON_COLLEAGUES        # verschiedene Ansprechpartner → evtl. Kollegen

    if not exact:                                       # nur fuzzy-ähnlich → Abschlag
        score *= 0.6
        if reason == REASON_COLLEAGUES:
            reason = REASON_FUZZY
    return round(score, 2), reason


def _completeness(m: dict) -> int:
    return sum(bool(m.get(f)) for f in
               ("email", "website", "phone", "address", "contact_name", "role"))


def suggest_keeper(members: list[dict]) -> str:
    """Behalten-Vorschlag: die meisten Aktivitäten, dann vollständigster,
    dann ältester. Gibt die `id` (als str) zurück."""
    def key(m: dict):
        return (-int(m.get("activity_count") or 0), -_completeness(m),
                str(m.get("created_at") or ""))
    return str(min(members, key=key)["id"])


def find_groups(leads: list[dict], *, fuzzy: bool = True) -> list[dict]:
    """Kandidaten-Duplikatgruppen (≥2 Mitglieder), nach Konfidenz sortiert.
    `leads`: Dicts mit mind. `id`, `company`, `contact_name` (weitere Felder
    werden 1:1 in die Member übernommen)."""
    n = len(leads)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    norms = [norm_company(le.get("company")) for le in leads]

    # 1) Exakt gleicher normalisierter Firmenname → zusammenfassen.
    by_norm: dict[str, list[int]] = {}
    for i, nm in enumerate(norms):
        if nm:
            by_norm.setdefault(nm, []).append(i)
    for idxs in by_norm.values():
        for k in idxs[1:]:
            union(idxs[0], k)

    # 2) Fuzzy: nur innerhalb eines Blocks (erste 4 Zeichen) paarweise prüfen.
    if fuzzy:
        blocks: dict[str, list[int]] = {}
        for i, nm in enumerate(norms):
            if nm:
                blocks.setdefault(nm[:4], []).append(i)
        for idxs in blocks.values():
            for a in range(len(idxs)):
                for b in range(a + 1, len(idxs)):
                    i, j = idxs[a], idxs[b]
                    if find(i) == find(j):
                        continue
                    if trigram_similarity(norms[i], norms[j]) >= FUZZY_THRESHOLD:
                        union(i, j)

    # 3) Cluster ≥2 einsammeln + scoren.
    clusters: dict[int, list[int]] = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(i)

    groups: list[dict] = []
    for idxs in clusters.values():
        if len(idxs) < 2:
            continue
        members = [leads[i] for i in idxs]
        score, reason = score_group(members)
        groups.append({
            "score": score,
            "reason": reason,
            "suggested_keeper_id": suggest_keeper(members),
            "members": members,
        })
    groups.sort(key=lambda g: -g["score"])
    return groups
