#!/bin/bash
# shellcheck disable=SC2034

apply_postfix_settings() {
  local setting
  local key
  local value
  for setting in ${!POSTFIX_*}; do
    key="${setting:8}"
    value="${!setting}"
    if [ -n "${value}" ]; then
      echo "applying custom postfix setting: ${key}=${value}"
      postconf "${key}=${value}"
    else
      echo "deleting custom postfix setting: ${key}"
      postconf -# "${key}"
    fi
  done
}

set -e

POSTFIX_maillog_file=/dev/stdout
POSTFIX_inet_protocols=all
POSTFIX_mydestination=
POSTFIX_relaydomains=

# We need to authenticate to our relayhost
POSTFIX_smtp_sasl_auth_enable=yes
POSTFIX_smtp_sasl_password_maps=lmdb:/etc/postfix/sasl_passwd

# Set "noanonymous" here enables SASL PLAIN logins
POSTFIX_smtp_sasl_security_options=noanonymous

# Require encryption since we're transmitting passwords.
POSTFIX_smtp_tls_security_level=encrypt

# Assume we're using SMTP-over-SSL when using port 465 (unless
# smtp_tls_wappermode has been set explicitly).
if [[ "${POSTFIX_smtp_tls_wrappermode:-unset}" = unset ]] && [[ "$POSTFIX_relayhost" =~ ":465" ]]; then
  POSTFIX_smtp_tls_wrappermode=yes
fi

apply_postfix_settings

if [[ "$POSTFIX_relayhost" ]] && [[ "$RELAYHOST_USER" ]] && [[ "$RELAYHOST_PASSWORD" ]]; then
  cat >/etc/postfix/sasl_passwd <<EOF
$POSTFIX_relayhost $RELAYHOST_USER:$RELAYHOST_PASSWORD
EOF
fi

postconf -M "lmtp/unix=lmtp unix  n - n - - smtpd"
postconf -MX smtp/inet

postmap /etc/postfix/sasl_passwd
newaliases

exec "$@"
