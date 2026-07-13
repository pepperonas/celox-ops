-- E-Mail-Qualitätsurteil je Lead (services/email_verifier.py). Additiv, nullable
-- (NULL = ungeprüft). Vor dem Code-Deploy einspielen (rückwärtskompatibel).
ALTER TABLE rainmaker_leads
  ADD COLUMN IF NOT EXISTS email_status varchar(20);
