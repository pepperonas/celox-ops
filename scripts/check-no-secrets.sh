#!/usr/bin/env bash
# Pre-commit hook: blocks accidental committing of secrets in staged files.
# Pattern: KEY=value (where value is non-empty and not a placeholder/var-ref)
set -e

PATTERN='(JWT_SECRET|TOTP_SECRET|SMTP_PASSWORD|GITHUB_TOKEN|ADMIN_PASSWORD_HASH|SENTRY_DSN|ICAL_TOKEN)\s*=\s*[^$#]'

found=0
for f in "$@"; do
  # Skip the example/template file
  if [[ "$f" == *.env.example ]] || [[ "$f" == "CLAUDE.md" ]]; then
    continue
  fi
  if grep -lE "$PATTERN" "$f" 2>/dev/null; then
    found=1
  fi
done

if [ "$found" -eq 1 ]; then
  echo "ABORT: Secret-looking values found in staged files. Remove or move to .env."
  exit 1
fi
exit 0
