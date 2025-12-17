#!/bin/bash

# --- CONFIGURATION ---
DOMAIN="line.yfgfiusustgf.cfd"
SS_PASSWORD="Google1500"
TCP_PATH="tcp-$(openssl rand -hex 8)"
UDP_PATH="udp-$(openssl rand -hex 8)"
LISTEN_PORT="8080"
# ---------------------

set -e

# 1. Install Certbot & Caddy
echo "--- Installing Certbot, Caddy, and ACL ---"
sudo apt-get update
sudo apt-get install -y certbot debian-keyring debian-archive-keyring apt-transport-https curl acl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt-get update && sudo apt-get install caddy -y

# 2. Setup Outline Binary in CURRENT FOLDER
echo "--- Downloading Outline Binary to $(pwd) ---"
wget -q https://github.com/Jigsaw-Code/outline-ss-server/releases/download/v1.7.2/outline-ss-server_1.9.2_linux_x86_64.tar.gz
tar -xzvf outline-ss-server_1.9.2_linux_x86_64.tar.gz
chmod +x outline-ss-server
rm outline-ss-server_1.9.2_linux_x86_64.tar.gz

# 3. Create config.yaml in CURRENT FOLDER
echo "--- Creating config.yaml ---"
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
        - id: "1"
          cipher: chacha20-ietf-poly1305
          secret: "$SS_PASSWORD"
EOF

# 4. Check and Remove Existing Caddyfile
echo "--- Checking for existing Caddyfile ---"
if [ -f /etc/caddy/Caddyfile ]; then
    echo "Found existing Caddyfile. Backing up to /etc/caddy/Caddyfile.bak and removing original..."
    sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak
    sudo rm /etc/caddy/Caddyfile
fi

# 5. Create NEW Caddyfile in /etc/caddy/
echo "--- Creating new /etc/caddy/Caddyfile ---"
sudo tee /etc/caddy/Caddyfile > /dev/null <<EOF
$DOMAIN:443 {
    # SSL: Point to the Certbot certificates
    tls /etc/letsencrypt/live/$DOMAIN/fullchain.pem /etc/letsencrypt/live/$DOMAIN/privkey.pem

    # Proxy: Forward traffic to Outline
    reverse_proxy 127.0.0.1:$LISTEN_PORT
}
EOF

echo "------------------------------------------------"
echo "✅ CLEAN CONFIGURATION COMPLETE"
echo "------------------------------------------------"
echo "STEP 1: Stop Caddy to release Port 80 for Certbot"
echo "   sudo systemctl stop caddy"
echo ""
echo "STEP 2: Generate SSL with Certbot"
echo "   sudo certbot certonly --standalone -d $DOMAIN"
echo ""
echo "STEP 3: Fix Permissions (Crucial for Caddy to read Certbot files)"
echo "   sudo setfacl -R -m u:caddy:rx /etc/letsencrypt/live/"
echo "   sudo setfacl -R -m u:caddy:rx /etc/letsencrypt/archive/"
echo ""
echo "STEP 4: Start Outline and Caddy"
echo "   nohup ./outline-ss-server -config config.yaml > outline.log 2>&1 &"
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
      url: wss://$DOMAIN/$TCP_PATH
    cipher: chacha20-ietf-poly1305
    secret: $SS_PASSWORD
  udp:
    \$type: shadowsocks
    endpoint:
      \$type: websocket
      url: wss://$DOMAIN/$UDP_PATH
    cipher: chacha20-ietf-poly1305
    secret: $SS_PASSWORD
EOF
