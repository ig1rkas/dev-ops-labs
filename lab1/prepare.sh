#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p certs auth evidence
if [[ ! -f certs/lab.key || ! -f certs/lab.crt ]]; then
  openssl req -x509 -newkey rsa:2048 -nodes -days 30 \
    -keyout certs/lab.key -out certs/lab.crt \
    -subj '/CN=idioma.local' -config openssl.cnf -extensions v3_req
fi
if [[ ! -f auth/.htpasswd ]]; then
  printf 'admin:' > auth/.htpasswd
  openssl passwd -apr1 'local-lab-password' >> auth/.htpasswd
fi
chmod 600 certs/lab.key
chmod 644 auth/.htpasswd
printf 'Prepared self-signed TLS and local Basic Auth.\n'
