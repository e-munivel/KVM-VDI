#!/bin/sh
# Set debug path password
PASSWD=$(python3 -c 'import os,crypt,getpass; print(crypt.crypt(os.environ["WEBAPP_ADMIN_PWD"], crypt.mksalt(crypt.METHOD_SHA512)))')
sed -i "/^    user admin password/c\    user admin password $PASSWD" /usr/local/etc/haproxy/haproxy.cfg

LETSENCRYPT_DOMAIN="$DOMAIN" LETSENCRYPT_EMAIL="$LETSENCRYPT_EMAIL" letsencrypt.sh
