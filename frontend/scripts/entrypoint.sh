#!/bin/sh
set -e

required_vars="NEXTAUTH_SECRET NEXTAUTH_URL AZURE_CLIENT_ID AZURE_CLIENT_SECRET AZURE_TENANT_ID"
for var in $required_vars; do
  eval val=\$$var
  if [ -z "$val" ]; then
    echo "Missing required env var: $var" >&2
    exit 1
  fi
done

exec npm run dev -- -H 0.0.0.0 -p 3000
