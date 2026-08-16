#!/bin/bash

set -e

# ==========================================================
# CONFIG
# ==========================================================

REPO="https://github.com/fallahali200/mybot.git"

APP_DIR="/var/www/bot"
VENV="$APP_DIR/env"

PEAK_SERVICE="/etc/systemd/system/peak.service"
BOT_SERVICE="/etc/systemd/system/bot.service"


# ==========================================================
# COLORS
# ==========================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'


# ==========================================================
# ROOT
# ==========================================================

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Run this script with sudo.${NC}"
    echo
    echo "sudo bash install.sh"
    exit 1
fi


# ==========================================================
# DOMAIN
# ==========================================================

get_domain() {

    read -p "Enter your domain: " DOMAIN

    DOMAIN=$(echo "$DOMAIN" \
        | sed 's#https://##' \
        | sed 's#http://##' \
        | sed 's#/$##')

    if [ -z "$DOMAIN" ]; then
        echo -e "${RED}Domain cannot be empty.${NC}"
        exit 1
    fi

    echo
    echo "Domain: $DOMAIN"
    echo
}


# ==========================================================
# INSTALL
# ==========================================================

install_app() {

    get_domain


    echo "=========================================="
    echo "Updating system..."
    echo "=========================================="

    apt update
    apt upgrade -y


    echo
    echo "=========================================="
    echo "Installing Nginx..."
    echo "=========================================="

    apt install nginx -y


    echo
    echo "=========================================="
    echo "Installing Certbot..."
    echo "=========================================="

    apt install certbot python3-certbot-nginx -y


    echo
    echo "=========================================="
    echo "Stopping Nginx..."
    echo "=========================================="

    systemctl stop nginx || true


    echo
    echo "=========================================="
    echo "Getting SSL certificate..."
    echo "=========================================="

    certbot certonly \
        --standalone \
        --agree-tos \
        --register-unsafely-without-email \
        -d "$DOMAIN"


    echo
    echo "Starting Nginx..."

    systemctl start nginx


    # ======================================================
    # APP DIRECTORY
    # ======================================================

    echo
    echo "=========================================="
    echo "Creating application directory..."
    echo "=========================================="

    rm -rf "$APP_DIR"

    mkdir -p "$APP_DIR"


    # ======================================================
    # PYTHON VENV
    # ======================================================

    echo
    echo "=========================================="
    echo "Installing Python venv..."
    echo "=========================================="

    apt install python3.12-venv -y


    echo
    echo "Creating virtual environment..."

    python3 -m venv "$VENV"


    echo
    echo "Activating virtual environment..."

    source "$VENV/bin/activate"


    # ======================================================
    # GIT
    # ======================================================

    echo
    echo "=========================================="
    echo "Installing Git..."
    echo "=========================================="

    apt install git -y


    # ======================================================
    # CLONE
    # ======================================================

    echo
    echo "=========================================="
    echo "Cloning GitHub project..."
    echo "=========================================="

    rm -rf "$APP_DIR"

    git clone "$REPO" "$APP_DIR"


    cd "$APP_DIR"

    source "$VENV/bin/activate"


    # ======================================================
    # PYTHON PACKAGES
    # ======================================================

    echo
    echo "=========================================="
    echo "Installing Python packages..."
    echo "=========================================="

    pip install flask \
        pytelegrambotapi \
        "requests[socks]" \
        "qrcode[pil]" \
        gunicorn \
        paramiko \
        pandas \
        pandas_ta \
        yfinance \
        quart \
        aiohttp


    # ======================================================
    # PEAK SERVICE
    # ======================================================

    echo
    echo "=========================================="
    echo "Creating peak.service..."
    echo "=========================================="

    cat > "$PEAK_SERVICE" <<EOF
[Unit]
Description=Gunicorn instance to serve Flask app
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV/bin"
ExecStart=$VENV/bin/gunicorn --workers 3 --bind unix:$APP_DIR/peak.sock app:app

[Install]
WantedBy=multi-user.target
EOF


    # ======================================================
    # BOT SERVICE
    # ======================================================

    echo
    echo "=========================================="
    echo "Creating bot.service..."
    echo "=========================================="

    cat > "$BOT_SERVICE" <<EOF
[Unit]
Description=Telegram Bot Service
After=network.target

[Service]
WorkingDirectory=$APP_DIR
ExecStart=$VENV/bin/python $APP_DIR/tel.py
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF


    # ======================================================
    # SYSTEMD
    # ======================================================

    echo
    echo "=========================================="
    echo "Starting systemd services..."
    echo "=========================================="

    systemctl daemon-reload

    systemctl enable peak
    systemctl start peak

    systemctl enable bot
    systemctl start bot


    # ======================================================
    # NGINX CONFIG
    # ======================================================

    echo
    echo "=========================================="
    echo "Creating Nginx configuration..."
    echo "=========================================="

    NGINX_CONFIG="/etc/nginx/sites-available/nginx.conf"

    cat > "$NGINX_CONFIG" <<EOF

# HTTP -> HTTPS

server {
    listen 80;

    server_name $DOMAIN www.$DOMAIN;

    return 301 https://\$host\$request_uri;
}


# HTTPS

server {
    listen 443 ssl;

    server_name $DOMAIN www.$DOMAIN;


    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;

    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;


    ssl_protocols TLSv1.2 TLSv1.3;

    ssl_ciphers HIGH:!aNULL:!MD5;


    location / {

        include proxy_params;

        proxy_pass http://unix:$APP_DIR/peak.sock;

    }


    location /gx/ {

        include proxy_params;

        proxy_pass http://unix:$APP_DIR/sub.sock;

    }

}

EOF


    # ======================================================
    # NGINX ENABLE
    # ======================================================

    echo
    echo "=========================================="
    echo "Enabling Nginx configuration..."
    echo "=========================================="

    rm -f /etc/nginx/sites-enabled/default

    rm -f /etc/nginx/sites-enabled/nginx.conf

    ln -s \
        /etc/nginx/sites-available/nginx.conf \
        /etc/nginx/sites-enabled/nginx.conf


    # ======================================================
    # PERMISSIONS
    # ======================================================

    echo
    echo "=========================================="
    echo "Setting permissions..."
    echo "=========================================="

    chown -R root:www-data "$APP_DIR"

    chmod 750 "$APP_DIR"


    # ======================================================
    # NGINX TEST
    # ======================================================

    echo
    echo "=========================================="
    echo "Testing Nginx..."
    echo "=========================================="

    nginx -t


    # ======================================================
    # RESTART NGINX
    # ======================================================

    systemctl restart nginx


    # ======================================================
    # CERTBOT AUTO RENEWAL
    # ======================================================

    echo
    echo "=========================================="
    echo "Enabling SSL auto renewal..."
    echo "=========================================="

    systemctl enable certbot.timer

    systemctl start certbot.timer


    # ======================================================
    # FINAL
    # ======================================================

    echo
    echo
    echo "=========================================="
    echo -e "${GREEN}INSTALLATION COMPLETED${NC}"
    echo "=========================================="
    echo

    echo "Domain:"
    echo "https://$DOMAIN"

    echo
    echo "Application:"
    echo "$APP_DIR"

    echo
    echo "GitHub:"
    echo "$REPO"

    echo
    echo "=========================================="
    echo "PEAK STATUS"
    echo "=========================================="

    systemctl status peak --no-pager || true

    echo
    echo "=========================================="
    echo "BOT STATUS"
    echo "=========================================="

    systemctl status bot --no-pager || true

    echo
    echo "=========================================="
    echo "NGINX STATUS"
    echo "=========================================="

    systemctl status nginx --no-pager || true

    echo
    echo -e "${GREEN}DONE${NC}"
}


# ==========================================================
# REMOVE
# ==========================================================

remove_app() {

    echo
    echo "=========================================="
    echo "REMOVE EVERYTHING"
    echo "=========================================="
    echo

    read -p "Enter domain: " DOMAIN

    DOMAIN=$(echo "$DOMAIN" \
        | sed 's#https://##' \
        | sed 's#http://##' \
        | sed 's#/$##')


    if [ -z "$DOMAIN" ]; then
        echo -e "${RED}Domain cannot be empty.${NC}"
        exit 1
    fi


    echo
    echo -e "${YELLOW}WARNING!${NC}"
    echo
    echo "This will remove:"
    echo
    echo "$APP_DIR"
    echo "peak.service"
    echo "bot.service"
    echo "Nginx configuration"
    echo "SSL certificate"
    echo


    read -p "Type YES to continue: " CONFIRM


    if [ "$CONFIRM" != "YES" ]; then

        echo "Cancelled."

        exit 0

    fi


    echo
    echo "Stopping services..."


    systemctl stop peak 2>/dev/null || true

    systemctl stop bot 2>/dev/null || true


    echo "Disabling services..."


    systemctl disable peak 2>/dev/null || true

    systemctl disable bot 2>/dev/null || true


    echo "Removing systemd files..."


    rm -f "$PEAK_SERVICE"

    rm -f "$BOT_SERVICE"


    systemctl daemon-reload


    echo "Removing Nginx..."


    rm -f /etc/nginx/sites-enabled/nginx.conf

    rm -f /etc/nginx/sites-available/nginx.conf


    if nginx -t >/dev/null 2>&1; then

        systemctl restart nginx

    fi


    echo "Removing application..."


    rm -rf "$APP_DIR"


    echo "Removing SSL certificate..."


    certbot delete \
        --cert-name "$DOMAIN" \
        --non-interactive 2>/dev/null || true


    echo
    echo "=========================================="
    echo -e "${GREEN}REMOVAL COMPLETED${NC}"
    echo "=========================================="
    echo
}


# ==========================================================
# MENU
# ==========================================================

while true
do

    clear

    echo "=========================================="
    echo "             SERVER INSTALLER"
    echo "=========================================="
    echo

    echo "1) Install"
    echo "2) Remove everything"
    echo "3) Exit"

    echo

    read -p "Select option [1-3]: " OPTION


    case "$OPTION" in

        1)

            install_app

            exit 0

            ;;


        2)

            remove_app

            exit 0

            ;;


        3)

            echo "Exit."

            exit 0

            ;;


        *)

            echo
            echo -e "${RED}Invalid option.${NC}"

            sleep 2

            ;;

    esac

done
