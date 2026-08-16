#!/bin/bash

# ==========================================================
# SERVER INSTALLER
# ==========================================================

set -u

# ==========================================================
# CONFIG
# ==========================================================

REPO="https://github.com/fallahali200/mybot.git"

APP_DIR="/var/www/bot"
VENV="$APP_DIR/env"

PEAK_SERVICE="/etc/systemd/system/peak.service"
BOT_SERVICE="/etc/systemd/system/bot.service"

NGINX_CONFIG="/etc/nginx/sites-available/nginx.conf"


# ==========================================================
# COLORS
# ==========================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'


# ==========================================================
# ROOT CHECK
# ==========================================================

if [ "$EUID" -ne 0 ]; then

    echo -e "${RED}Please run this script with sudo.${NC}"
    echo
    echo "Example:"
    echo
    echo "sudo bash install.sh"
    echo

    exit 1
fi


# ==========================================================
# DOMAIN CLEAN
# ==========================================================

clean_domain() {

    local DOMAIN="$1"

    DOMAIN=$(echo "$DOMAIN" \
        | sed 's#https://##' \
        | sed 's#http://##' \
        | sed 's#/$##')

    echo "$DOMAIN"
}


# ==========================================================
# INSTALL
# ==========================================================

install_app() {

    echo
    echo "=========================================="
    echo "             INSTALLATION"
    echo "=========================================="
    echo


    # ======================================================
    # DOMAIN
    # ======================================================

    read -p "Enter your domain: " DOMAIN

    DOMAIN=$(clean_domain "$DOMAIN")


    if [ -z "$DOMAIN" ]; then

        echo -e "${RED}Domain cannot be empty.${NC}"

        exit 1

    fi


    echo
    echo -e "${GREEN}Domain:${NC} $DOMAIN"
    echo -e "${GREEN}GitHub:${NC} $REPO"
    echo


    read -p "Continue installation? [y/N]: " CONFIRM


    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then

        echo
        echo "Installation cancelled."

        exit 0

    fi


    # ======================================================
    # UPDATE SYSTEM
    # ======================================================

    echo
    echo "=========================================="
    echo "Updating system..."
    echo "=========================================="

    apt update

    if [ $? -ne 0 ]; then

        echo -e "${RED}apt update failed.${NC}"

        exit 1

    fi


    apt upgrade -y


    # ======================================================
    # INSTALL NGINX
    # ======================================================

    echo
    echo "=========================================="
    echo "Installing Nginx..."
    echo "=========================================="

    apt install nginx -y


    # ======================================================
    # INSTALL CERTBOT
    # ======================================================

    echo
    echo "=========================================="
    echo "Installing Certbot..."
    echo "=========================================="

    apt install \
        certbot \
        python3-certbot-nginx \
        -y


    # ======================================================
    # INSTALL GIT
    # ======================================================

    echo
    echo "=========================================="
    echo "Installing Git..."
    echo "=========================================="

    apt install git -y


    # ======================================================
    # INSTALL PYTHON VENV
    # ======================================================

    echo
    echo "=========================================="
    echo "Installing Python venv..."
    echo "=========================================="

    apt install python3-venv -y


    # ======================================================
    # STOP NGINX
    # ======================================================

    echo
    echo "Stopping Nginx..."

    systemctl stop nginx 2>/dev/null || true


    # ======================================================
    # SSL CERTIFICATE
    # ======================================================

    echo
    echo "=========================================="
    echo "Getting SSL certificate..."
    echo "=========================================="

    certbot certonly \
        --standalone \
        --agree-tos \
        --register-unsafely-without-email \
        -d "$DOMAIN"


    if [ $? -ne 0 ]; then

        echo
        echo -e "${RED}SSL certificate installation failed.${NC}"
        echo
        echo "Make sure:"
        echo "1. Domain points to this server."
        echo "2. Port 80 is open."
        echo "3. No other service is using port 80."
        echo

        exit 1

    fi


    # ======================================================
    # START NGINX
    # ======================================================

    systemctl start nginx


    # ======================================================
    # APPLICATION DIRECTORY
    # ======================================================

    echo
    echo "=========================================="
    echo "Preparing application directory..."
    echo "=========================================="


    rm -rf "$APP_DIR"

    mkdir -p /var/www


    # ======================================================
    # CLONE GITHUB
    # ======================================================

    echo
    echo "=========================================="
    echo "Cloning GitHub repository..."
    echo "=========================================="

    git clone "$REPO" "$APP_DIR"


    if [ $? -ne 0 ]; then

        echo
        echo -e "${RED}Git clone failed.${NC}"
        echo

        exit 1

    fi


    # ======================================================
    # CHECK PROJECT
    # ======================================================

    cd "$APP_DIR"


    echo
    echo "Project files:"

    ls -la

    echo


    if [ ! -f "$APP_DIR/app.py" ]; then

        echo -e "${RED}ERROR: app.py not found.${NC}"

        exit 1

    fi


    if [ ! -f "$APP_DIR/tel.py" ]; then

        echo -e "${YELLOW}WARNING: tel.py not found.${NC}"

    fi


    # ======================================================
    # CREATE VENV
    # ======================================================

    echo
    echo "=========================================="
    echo "Creating Python virtual environment..."
    echo "=========================================="


    rm -rf "$VENV"


    python3 -m venv "$VENV"


    if [ ! -f "$VENV/bin/python" ]; then

        echo -e "${RED}Python virtual environment creation failed.${NC}"

        exit 1

    fi


    # ======================================================
    # PIP
    # ======================================================

    echo
    echo "Upgrading pip..."


    "$VENV/bin/python" -m pip install --upgrade pip


    # ======================================================
    # PYTHON PACKAGES
    # ======================================================

    echo
    echo "=========================================="
    echo "Installing Python packages..."
    echo "=========================================="


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


    if [ $? -ne 0 ]; then

        echo
        echo -e "${RED}Python package installation failed.${NC}"

        exit 1

    fi


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
Restart=always
RestartSec=5

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
User=root
Group=www-data
WorkingDirectory=$APP_DIR
ExecStart=$VENV/bin/python $APP_DIR/tel.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target

EOF


    # ======================================================
    # SYSTEMD RELOAD
    # ======================================================

    echo
    echo "=========================================="
    echo "Configuring systemd..."
    echo "=========================================="


    systemctl daemon-reload


    systemctl enable peak

    systemctl enable bot


    # ======================================================
    # NGINX CONFIG
    # ======================================================

    echo
    echo "=========================================="
    echo "Creating Nginx configuration..."
    echo "=========================================="


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


    if [ $? -ne 0 ]; then

        echo
        echo -e "${RED}Nginx configuration test failed.${NC}"

        exit 1

    fi


    # ======================================================
    # START PEAK
    # ======================================================

    echo
    echo "Starting peak..."

    systemctl restart peak


    sleep 2


    # ======================================================
    # START BOT
    # ======================================================

    echo
    echo "Starting bot..."

    systemctl restart bot


    sleep 2


    # ======================================================
    # START NGINX
    # ======================================================

    echo
    echo "Starting Nginx..."

    systemctl enable nginx

    systemctl restart nginx


    # ======================================================
    # CERTBOT AUTO RENEWAL
    # ======================================================

    echo
    echo "=========================================="
    echo "Configuring SSL auto renewal..."
    echo "=========================================="


    systemctl enable certbot.timer

    systemctl start certbot.timer


    # ======================================================
    # RENEWAL TEST
    # ======================================================

    echo
    echo "Testing SSL renewal..."

    certbot renew --dry-run || true


    # ======================================================
    # STATUS
    # ======================================================

    echo
    echo
    echo "=========================================="
    echo -e "${GREEN}INSTALLATION FINISHED${NC}"
    echo "=========================================="
    echo


    echo -e "${BLUE}Website:${NC}"

    echo "https://$DOMAIN"


    echo
    echo -e "${BLUE}Application:${NC}"

    echo "$APP_DIR"


    echo
    echo -e "${BLUE}GitHub:${NC}"

    echo "$REPO"


    echo
    echo "=========================================="
    echo "PEAK STATUS"
    echo "=========================================="


    systemctl --no-pager status peak || true


    echo
    echo "=========================================="
    echo "BOT STATUS"
    echo "=========================================="


    systemctl --no-pager status bot || true


    echo
    echo "=========================================="
    echo "NGINX STATUS"
    echo "=========================================="


    systemctl --no-pager status nginx || true


    echo
    echo "=========================================="
    echo -e "${GREEN}DONE${NC}"
    echo "=========================================="
    echo


    read -p "Press Enter to exit..."
}


# ==========================================================
# REMOVE
# ==========================================================

remove_app() {

    echo
    echo "=========================================="
    echo "          REMOVE EVERYTHING"
    echo "=========================================="
    echo


    read -p "Enter domain: " DOMAIN

    DOMAIN=$(clean_domain "$DOMAIN")


    if [ -z "$DOMAIN" ]; then

        echo -e "${RED}Domain cannot be empty.${NC}"

        exit 1

    fi


    echo
    echo -e "${YELLOW}WARNING!${NC}"
    echo
    echo "The following will be removed:"
    echo
    echo "  $APP_DIR"
    echo "  peak.service"
    echo "  bot.service"
    echo "  Nginx configuration"
    echo "  SSL certificate for $DOMAIN"
    echo


    read -p "Type YES to continue: " CONFIRM


    if [ "$CONFIRM" != "YES" ]; then

        echo
        echo "Cancelled."

        exit 0

    fi


    echo
    echo "Stopping peak..."

    systemctl stop peak 2>/dev/null || true


    echo "Stopping bot..."

    systemctl stop bot 2>/dev/null || true


    echo "Disabling services..."

    systemctl disable peak 2>/dev/null || true

    systemctl disable bot 2>/dev/null || true


    echo "Removing systemd files..."

    rm -f "$PEAK_SERVICE"

    rm -f "$BOT_SERVICE"


    systemctl daemon-reload


    echo "Removing Nginx configuration..."

    rm -f /etc/nginx/sites-enabled/nginx.conf

    rm -f /etc/nginx/sites-available/nginx.conf


    echo "Removing application..."

    rm -rf "$APP_DIR"


    echo "Removing SSL certificate..."

    certbot delete \
        --cert-name "$DOMAIN" \
        --non-interactive 2>/dev/null || true


    if nginx -t >/dev/null 2>&1; then

        systemctl restart nginx

    fi


    echo
    echo "=========================================="
    echo -e "${GREEN}REMOVAL COMPLETED${NC}"
    echo "=========================================="
    echo


    read -p "Press Enter to exit..."
}


# ==========================================================
# MENU
# ==========================================================

while true
do

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

            install_app

            exit 0

            ;;


        2)

            remove_app

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
