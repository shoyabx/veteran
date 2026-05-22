#!/bin/sh
set -e

required_vars="DATABASE_URL JWT_SECRET_KEY TOKEN_ENCRYPTION_KEY"
for var in $required_vars; do
  eval val=\$$var
  if [ -z "$val" ]; then
    echo "Missing required env var: $var" >&2
    exit 1
  fi
done

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
