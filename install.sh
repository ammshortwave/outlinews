#!/bin/bash

# --- CONFIGURATION ---
DOMAIN="line.yfgfiusustgf.cfd"
LISTEN_PORT="5000"  # Internal Outline Port
CADDY_PORT="8443"   # Public Caddy Port

# YOUR SPECIFIC KEY DATA
KEY_ID="1"
KEY_NAME="short"
KEY_SECRET="bamwJXISjGZxcQhgtos7"
KEY_EXPIRE="2025-12-01"

TCP_PATH="tcp-$(openssl rand -hex 8)"
UDP_PATH="udp-$(openssl rand -hex 8)"
# ---------------------

set -e

echo "--- Installing Certbot, Caddy, and ACL ---"
sudo apt-get update
sudo apt-get install -y certbot debian-keyring debian-archive-keyring apt-transport-https curl acl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update && sudo apt-get install caddy -y

echo "--- Downloading Outline SS Server v1.9.2 to $(pwd) ---"
wget -q https://github.com/Jigsaw-Code/outline-ss-server/releases/download/v1.9.2/outline-ss-server_1.9.2_linux_x86_64.tar.gz
tar -xzvf outline-ss-server_1.9.2_linux_x86_64.tar.gz
chmod +x outline-ss-server
rm outline-ss-server_1.9.2_linux_x86_64.tar.gz

echo "--- Creating config.yaml with Expiry Date ---"
cat <<EOF > config.yaml
web:
  servers:
    - id: server1
      listen: [ "127.0.0.1:$LISTEN_PORT" ]
services:
    - listeners:
        - type: websocket-stream
          web_server: server1
          path: "/$TCP_PATH"
        - type: websocket-packet
          web_server: server1
          path: "/$UDP_PATH"
      keys:
        - id: "$KEY_ID"
          name: "$KEY_NAME"
          cipher: chacha20-ietf-poly1305
          secret: "$KEY_SECRET"
          expire_date: "$KEY_EXPIRE"
EOF

echo "--- Cleaning and Creating /etc/caddy/Caddyfile ---"
if [ -f /etc/caddy/Caddyfile ]; then
    sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak
    sudo rm /etc/caddy/Caddyfile
fi

sudo tee /etc/caddy/Caddyfile > /dev/null <<EOF
$DOMAIN:$CADDY_PORT {
    tls /etc/letsencrypt/live/$DOMAIN/fullchain.pem /etc/letsencrypt/live/$DOMAIN/privkey.pem
    reverse_proxy 127.0.0.1:$LISTEN_PORT
}
EOF

echo "------------------------------------------------"
echo "✅ SETUP READY (Key Expiry: $KEY_EXPIRE)"
echo "------------------------------------------------"
echo "STEP 1: Stop Caddy"
echo "   sudo systemctl stop caddy"
echo ""
echo "STEP 2: Generate SSL"
echo "   sudo certbot certonly --standalone -d $DOMAIN"
echo ""
echo "STEP 3: Fix Permissions"
echo "   sudo setfacl -R -m u:caddy:rx /etc/letsencrypt/live/"
echo "   sudo setfacl -R -m u:caddy:rx /etc/letsencrypt/archive/"
echo ""
echo "STEP 4: Start Outline"
echo "   nohup ./outline-ss-server -config config.yaml > outline.log 2>&1 &"
echo ""
echo "STEP 5: Start Caddy"
echo "   sudo systemctl start caddy"
echo "------------------------------------------------"
echo "YOUR DYNAMIC ACCESS KEY (FOR OUTLINE CLIENT):"
echo ""
cat <<EOF
transport:
  \$type: tcpudp
  tcp:
    \$type: shadowsocks
    endpoint:
      \$type: websocket
      url: wss://$DOMAIN:$CADDY_PORT/$TCP_PATH
    cipher: chacha20-ietf-poly1305
    secret: $KEY_SECRET
  udp:
    \$type: shadowsocks
    endpoint:
      \$type: websocket
      url: wss://$DOMAIN:$CADDY_PORT/$UDP_PATH
    cipher: chacha20-ietf-poly1305
    secret: $KEY_SECRET
EOF
