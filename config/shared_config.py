"""
This module provides the template for OpenVPN client configurations.
"""

CLIENT_TEMPLATE = """
client
dev tun
proto {proto}
remote {server_ip} {port}
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
verb 3
cipher AES-128-GCM
auth SHA256
tls-version-min 1.2

<ca>
{ca_cert}
</ca>

{user_specific_certs}

<tls-crypt>
{tls_crypt_key}
</tls-crypt>
"""

USER_CERTS_TEMPLATE = """
<cert>
{user_cert}
</cert>
<key>
{user_key}
</key>
"""
