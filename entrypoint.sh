#!/bin/bash

if [ ! -d "/var/run/secrets/" ]; then
	# If nobody mounted us secrets, make some of our own
	mkdir -p /var/run/secrets
	openssl req -x509 -out  /var/run/secrets/server.crt -keyout  /var/run/secrets/server.key \
	  -newkey rsa:2048 -nodes -sha256 \
	  -subj '/CN=localhost' -extensions EXT -config <( \
	   printf "[dn]\nCN=localhost\n[req]\ndistinguished_name = dn\n[EXT]\nsubjectAltName=DNS:localhost\nkeyUsage=digitalSignature\nextendedKeyUsage=serverAuth")
fi

exec python -u /main.py
