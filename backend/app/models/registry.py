"""Alle Modell-Module importieren — damit `Base.metadata` vollständig ist.

Wofür: Ein Wartungsskript (`app/scripts/*`) importiert normalerweise nur die
Modelle, mit denen es arbeitet. Dann fehlen aber die Ziel-Tabellen der
Fremdschlüssel — allen voran `users`, auf das `OwnedMixin.owner_id` zeigt. Ein
Trockenlauf (nur SELECT) läuft damit noch durch, und erst der schreibende Lauf
stirbt mit `NoReferencedTableError`, also genau dann, wenn man ihn braucht (live
passiert am 2026-07-29 mit `update_outreach_signature`).

Skripte schreiben deshalb EINE Zeile statt einer wachsenden Import-Liste:

    from app.models import registry  # noqa: F401

Bewusst ein eigenes Modul und nicht `app/models/__init__.py`: Dort würde jeder
`from app.models.x import Y`-Import im ganzen Projekt plötzlich alle 32
Modell-Module laden. Die Liste hält `test_smoke.py` vollständig — ein neues
Modell ohne Eintrag lässt den Test fallen.
"""

from app.models import activity  # noqa: F401
from app.models import ai_lead_run  # noqa: F401
from app.models import app_settings  # noqa: F401
from app.models import attachment  # noqa: F401
from app.models import audit_log  # noqa: F401
from app.models import compliance_record  # noqa: F401
from app.models import contract  # noqa: F401
from app.models import customer  # noqa: F401
from app.models import customer_todo_suggestion  # noqa: F401
from app.models import document_template  # noqa: F401
from app.models import email_template  # noqa: F401
from app.models import expense  # noqa: F401
from app.models import hostinger_link  # noqa: F401
from app.models import invoice  # noqa: F401
from app.models import lead  # noqa: F401
from app.models import market_baustein  # noqa: F401
from app.models import market_product  # noqa: F401
from app.models import lead_analysis_job  # noqa: F401
from app.models import lead_change_log  # noqa: F401
from app.models import lead_chat_import  # noqa: F401
from app.models import lead_website_analysis  # noqa: F401
from app.models import order  # noqa: F401
from app.models import outreach_template  # noqa: F401
from app.models import pagespeed_result  # noqa: F401
from app.models import rainmaker_activity  # noqa: F401
from app.models import rainmaker_goal  # noqa: F401
from app.models import rainmaker_lead  # noqa: F401
from app.models import rainmaker_lead_draft  # noqa: F401
from app.models import rainmaker_settings  # noqa: F401
from app.models import rainmaker_streak  # noqa: F401
from app.models import rainmaker_template  # noqa: F401
from app.models import reference_value  # noqa: F401
from app.models import time_entry  # noqa: F401
from app.models import todo  # noqa: F401
from app.models import user  # noqa: F401
