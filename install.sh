#!/bin/bash

set -e

# ==================================================
# CONFIG
# ==================================================

# آدرس GitHub پروژه
REPO="https://github.com/fallahali200/mybot.git"

# مسیر نصب پروژه
APP_DIR="/var/www/bot"

# محیط مجازی Python
VENV="$APP_DIR/env"


# ==================================================
# COLORS
# ==================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'


# ==================================================
# ROOT CHECK
# ==================================================

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run this script with sudo.${NC}"
    echo
    echo "Example:"
    echo "sudo bash install.sh"
    exit 1
fi


# ==================================================
# REMOVE EVERYTHING
# ==================================================

remove_all() {

    echo
    echo "=========================================="
    echo "          REMOVE EVERYTHING"
    echo "=========================================="
    echo

    read -p "Enter domain to remove: " DOMAIN

    if [ -z "$DOMAIN" ]; then
        echo -e "${RED}Domain cannot be empty.${NC}"
        exit 1
    fi

    DOMAIN=$(echo "$DOMAIN" \
        | sed 's~https://~~' \
        | sed 's~http://~~' \
        | sed 's~/~~g')

    echo
    echo -e "${YELLOW}WARNING!${NC}"
    echo
    echo "This will remove:"
    echo
    echo "  - peak.service"
    echo "  - bot.service"
    echo "  - Nginx configuration"
    echo "  - /var/www/bot"
    echo "  - SSL certificate"
    echo

    read -p "Type YES to continue: " CONFIRM

    if [ "$CONFIRM" != "YES" ]; then
        echo
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


    echo "Removing systemd services..."

    rm -f /etc/systemd/system/peak.service
    rm -f /etc/systemd/system/bot.service

    systemctl daemon-reload


    echo "Removing Nginx configuration..."

    rm -f "/etc/nginx/sites-enabled/$DOMAIN"
    rm -f "/etc/nginx/sites-available/$DOMAIN"

    if nginx -t >/dev/null 2>&1; then
        systemctl restart nginx
    fi


    echo "Removing application..."

    rm -rf "$APP_DIR"


    echo "Removing SSL certificate..."

    if command -v certbot >/dev/null 2>&1; then
        certbot delete \
            --cert-name "$DOMAIN" \
            --non-interactive 2>/dev/null || true
    fi


    echo
    echo "=========================================="
    echo -e "${GREEN}REMOVAL COMPLETED${NC}"
    echo "=========================================="
    echo
}


# ==================================================
# INSTALL
# ==================================================

install_all() {

    echo
    echo "=========================================="
    echo "             INSTALLATION"
    echo "=========================================="
    echo


    # ------------------------------------------
    # ASK DOMAIN
    # ------------------------------------------

    read -p "Enter your domain: " DOMAIN

    if [ -z "$DOMAIN" ]; then
        echo -e "${RED}Domain cannot be empty.${NC}"
        exit 1
    fi


    # Remove protocol and trailing slash

    DOMAIN=$(echo "$DOMAIN" \
        | sed 's~https://~~' \
        | sed 's~http://~~' \
        | sed 's~/~~g')


    echo
    echo "Domain:"
    echo "$DOMAIN"
    echo

    echo "GitHub:"
    echo "$REPO"
    echo


    # ------------------------------------------
    # CONFIRM
    # ------------------------------------------

    read -p "Continue installation? [y/N]: " CONFIRM

    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo
        echo "Cancelled."
        exit 0
    fi


    # ------------------------------------------
    # UPDATE SYSTEM
    # ------------------------------------------

    echo
    echo "=========================================="
    echo "Updating system..."
    echo "=========================================="

    apt update
    apt upgrade -y


    # ------------------------------------------
    # INSTALL PACKAGES
    # ------------------------------------------

    echo
    echo "Installing required packages..."

    apt install -y \
        nginx \
        git \
        curl \
        certbot \
        python3-certbot-nginx \
        python3-venv


    # ------------------------------------------
    # STOP OLD SERVICES
    # ------------------------------------------

    systemctl stop peak 2>/dev/null || true
    systemctl stop bot 2>/dev/null || true


    # ------------------------------------------
    # CREATE APP DIRECTORY
    # ------------------------------------------

    echo
    echo "Preparing application directory..."

    rm -rf "$APP_DIR"

    mkdir -p "$APP_DIR"


    # ------------------------------------------
    # CLONE GITHUB
    # ------------------------------------------

    echo
    echo "=========================================="
    echo "Cloning project from GitHub..."
    echo "=========================================="

    git clone "$REPO" "$APP_DIR"


    cd "$APP_DIR"


    # ------------------------------------------
    # PYTHON VIRTUAL ENVIRONMENT
    # ------------------------------------------

    echo
    echo "Creating Python virtual environment..."

    python3 -m venv "$VENV"


    echo "Upgrading pip..."

    "$VENV/bin/pip" install --upgrade pip


    # ------------------------------------------
    # INSTALL PYTHON DEPENDENCIES
    # ------------------------------------------

    echo
    echo "=========================================="
    echo "Installing Python dependencies..."
    echo "=========================================="

    if [ -f "$APP_DIR/requirements.txt" ]; then

        echo "requirements.txt found."

        "$VENV/bin/pip" install \
            -r "$APP_DIR/requirements.txt"

    else

        echo "requirements.txt not found."
        echo "Installing default packages..."

        "$VENV/bin/pip" install \
            flask \
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

    fi


    # ------------------------------------------
    # CHECK APP FILES
    # ------------------------------------------

    echo
    echo "Checking application files..."

    if [ ! -f "$APP_DIR/app.py" ]; then
        echo -e "${RED}WARNING: app.py not found!${NC}"
        echo "peak.service may fail."
    fi

    if [ ! -f "$APP_DIR/tel.py" ]; then
        echo -e "${RED}WARNING: tel.py not found!${NC}"
        echo "bot.service may fail."
    fi


    # ------------------------------------------
    # SSL CERTIFICATE
    # ------------------------------------------

    echo
    echo "=========================================="
    echo "Getting SSL certificate..."
    echo "=========================================="

    systemctl stop nginx || true


    certbot certonly \
        --standalone \
        --agree-tos \
        --register-unsafely-without-email \
        -d "$DOMAIN"


    systemctl start nginx


    # ------------------------------------------
    # PEAK SERVICE
    # ------------------------------------------

    echo
    echo "Creating peak.service..."

    cat > /etc/systemd/system/peak.service <<EOF
[Unit]
Description=Gunicorn Application Service
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV/bin"
ExecStart=$VENV/bin/gunicorn --workers 3 --bind unix:$APP_DIR/peak.sock app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF


    # ------------------------------------------
    # BOT SERVICE
    # ------------------------------------------

    echo
    echo "Creating bot.service..."

    cat > /etc/systemd/system/bot.service <<EOF
[Unit]
Description=Telegram Bot Service
After=network.target

[Service]
WorkingDirectory=$APP_DIR
ExecStart=$VENV/bin/python $APP_DIR/tel.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF


    # ------------------------------------------
    # NGINX CONFIGURATION
    # ------------------------------------------

    echo
    echo "=========================================="
    echo "Creating Nginx configuration..."
    echo "=========================================="

    NGINX_CONFIG="/etc/nginx/sites-available/$DOMAIN"


    cat > "$NGINX_CONFIG" <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name $DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;

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


    # ------------------------------------------
    # ENABLE NGINX SITE
    # ------------------------------------------

    echo
    echo "Enabling Nginx site..."

    rm -f /etc/nginx/sites-enabled/default

    ln -sf \
        "$NGINX_CONFIG" \
        "/etc/nginx/sites-enabled/$DOMAIN"


    # ------------------------------------------
    # PERMISSIONS
    # ------------------------------------------

    echo
    echo "Setting permissions..."

    chown -R root:www-data "$APP_DIR"

    chmod 750 "$APP_DIR"


    # ------------------------------------------
    # SYSTEMD
    # ------------------------------------------

    echo
    echo "=========================================="
    echo "Starting application services..."
    echo "=========================================="

    systemctl daemon-reload


    systemctl enable peak
    systemctl enable bot


    systemctl restart peak
    systemctl restart bot


    # ------------------------------------------
    # NGINX TEST
    # ------------------------------------------

    echo
    echo "Testing Nginx configuration..."

    nginx -t


    systemctl enable nginx

    systemctl restart nginx


    # ------------------------------------------
    # CERTBOT AUTO RENEWAL
    # ------------------------------------------

    echo
    echo "=========================================="
    echo "Enabling automatic SSL renewal..."
    echo "=========================================="

    systemctl enable certbot.timer

    systemctl start certbot.timer


    # ------------------------------------------
    # SSL RENEWAL TEST
    # ------------------------------------------

    echo
    echo "Testing certificate renewal..."

    certbot renew --dry-run


    # ------------------------------------------
    # FINAL STATUS
    # ------------------------------------------

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
    echo "------------------------------------------"
    echo "Peak service"
    echo "------------------------------------------"

    systemctl --no-pager --full status peak || true

    echo
    echo "------------------------------------------"
    echo "Bot service"
    echo "------------------------------------------"

    systemctl --no-pager --full status bot || true

    echo
    echo "------------------------------------------"
    echo "Nginx service"
    echo "------------------------------------------"

    systemctl --no-pager --full status nginx || true

    echo
    echo "=========================================="
    echo -e "${GREEN}DONE${NC}"
    echo "=========================================="
}


# ==================================================
# MENU
# ==================================================

while true; do

    clear

    echo "=========================================="
    echo "            SERVER INSTALLER"
    echo "=========================================="
    echo
    echo "1) Install"
    echo "2) Remove everything"
    echo "3) Exit"
    echo

    read -p "Select option [1-3]: " OPTION


    case "$OPTION" in

        1)
            install_all
            exit 0
            ;;

        2)
            remove_all
            exit 0
            ;;

        3)
            echo
            echo "Bye."
            exit 0
            ;;

        *)
            echo
            echo -e "${RED}Invalid option.${NC}"
            sleep 2
            ;;

    esac

done
