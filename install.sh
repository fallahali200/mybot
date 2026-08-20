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
TRADE_SERVICE="/etc/systemd/system/trade.service"
SUB_SERVICE="/etc/systemd/system/sub.service"

NGINX_CONFIG="/etc/nginx/sites-available/nginx.conf"

BACKUP_SCRIPT="$APP_DIR/backup.py"
BACKUP_LOG="/var/log/bot-backup.log"

TRADE_SCRIPT="$APP_DIR/trade.py"
TRADE_LOG="/var/log/bot-trade.log"

CURRENCIES_FILE="$APP_DIR/currencies.json"

DOMAIN=""
SUB_DOMAIN=""
INSTALL_SUB="no"


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

    local DOMAIN_INPUT="$1"

    DOMAIN_INPUT=$(echo "$DOMAIN_INPUT" \
        | sed 's#https://##' \
        | sed 's#http://##' \
        | sed 's#/$##' \
        | sed 's/[[:space:]]//g')

    echo "$DOMAIN_INPUT"

}


# ==========================================================
# CHECK COMMAND
# ==========================================================

check_command() {

    local COMMAND_NAME="$1"

    if ! command -v "$COMMAND_NAME" >/dev/null 2>&1; then

        echo -e "${RED}Required command not found: $COMMAND_NAME${NC}"

        exit 1

    fi

}


# ==========================================================
# VALIDATE DOMAIN
# ==========================================================

validate_domain() {

    local DOMAIN_INPUT="$1"

    if [ -z "$DOMAIN_INPUT" ]; then

        return 1

    fi


    if [[ ! "$DOMAIN_INPUT" =~ ^[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?$ ]]; then

        return 1

    fi


    return 0

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
    # MAIN DOMAIN
    # ======================================================

    read -p "Enter your main domain: " DOMAIN

    DOMAIN=$(clean_domain "$DOMAIN")


    if ! validate_domain "$DOMAIN"; then

        echo
        echo -e "${RED}Invalid main domain.${NC}"
        echo

        exit 1

    fi


    # ======================================================
    # SUB APPLICATION
    # ======================================================

    INSTALL_SUB="no"
    SUB_DOMAIN=""


    echo
    echo "=========================================="
    echo "          SUB APPLICATION"
    echo "=========================================="
    echo

    echo "Do you want to install the Sub application?"
    echo
    echo "If YES, a second domain will be requested."
    echo
    echo "Example:"
    echo
    echo "Main domain:"
    echo "  example.com"
    echo
    echo "Sub domain:"
    echo "  sub.example.com"
    echo
    echo "Routing:"
    echo
    echo "  https://example.com/*"
    echo "        -> peak.sock"
    echo
    echo "  https://sub.example.com/gx/*"
    echo "        -> sub.sock"
    echo


    read -p "Install Sub application? [y/N]: " SUB_CONFIRM


    if [[ "$SUB_CONFIRM" =~ ^[Yy]$ ]]; then

        INSTALL_SUB="yes"


        echo
        echo "=========================================="
        echo "             SUB DOMAIN"
        echo "=========================================="
        echo


        read -p "Enter Sub domain: " SUB_DOMAIN

        SUB_DOMAIN=$(clean_domain "$SUB_DOMAIN")


        if ! validate_domain "$SUB_DOMAIN"; then

            echo
            echo -e "${RED}Invalid Sub domain.${NC}"
            echo

            exit 1

        fi


        if [ "$SUB_DOMAIN" = "$DOMAIN" ]; then

            echo
            echo -e "${RED}Sub domain must be different from main domain.${NC}"
            echo

            exit 1

        fi


        echo
        echo -e "${GREEN}Sub application enabled.${NC}"
        echo
        echo "Main domain:"
        echo "  https://$DOMAIN/*"
        echo "        -> peak.sock"
        echo
        echo "Sub domain:"
        echo "  https://$SUB_DOMAIN/gx/*"
        echo "        -> sub.sock"


    else

        INSTALL_SUB="no"

        echo
        echo -e "${YELLOW}Sub application disabled.${NC}"
        echo
        echo "Everything -> peak.sock"

    fi


    # ======================================================
    # SUMMARY
    # ======================================================

    echo
    echo "=========================================="
    echo "INSTALLATION SUMMARY"
    echo "=========================================="
    echo

    echo -e "${GREEN}Main Domain:${NC} $DOMAIN"
    echo -e "${GREEN}GitHub:${NC} $REPO"


    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo -e "${GREEN}Sub:${NC} ENABLED"
        echo -e "${GREEN}Main URL:${NC} https://$DOMAIN/"
        echo -e "${GREEN}Main socket:${NC} $APP_DIR/peak.sock"
        echo -e "${GREEN}Sub domain:${NC} https://$SUB_DOMAIN/"
        echo -e "${GREEN}Sub URL:${NC} https://$SUB_DOMAIN/gx/"
        echo -e "${GREEN}Sub socket:${NC} $APP_DIR/sub.sock"

    else

        echo
        echo -e "${YELLOW}Sub:${NC} DISABLED"

    fi


    echo
    echo "Continue installation?"
    echo

    read -p "Continue? [y/N]: " CONFIRM


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
    # INSTALL PACKAGES
    # ======================================================

    echo
    echo "=========================================="
    echo "Installing required packages..."
    echo "=========================================="


    apt install \
        nginx \
        certbot \
        python3-certbot-nginx \
        git \
        python3-venv \
        python3-pip \
        cron \
        -y


    if [ $? -ne 0 ]; then

        echo -e "${RED}Required package installation failed.${NC}"

        exit 1

    fi


    # ======================================================
    # CHECK COMMANDS
    # ======================================================

    check_command nginx
    check_command certbot
    check_command git
    check_command python3
    check_command systemctl


    # ======================================================
    # CRON
    # ======================================================

    echo
    echo "=========================================="
    echo "Configuring Cron..."
    echo "=========================================="


    systemctl enable cron
    systemctl start cron


    # ======================================================
    # STOP NGINX
    # ======================================================

    echo
    echo "Stopping Nginx..."

    systemctl stop nginx 2>/dev/null || true


    # ======================================================
    # SSL MAIN DOMAIN
    # ======================================================

    echo
    echo "=========================================="
    echo "Getting SSL certificate..."
    echo "=========================================="
    echo

    echo "Main domain:"
    echo "$DOMAIN"
    echo


    certbot certonly \
        --standalone \
        --agree-tos \
        --register-unsafely-without-email \
        --non-interactive \
        -d "$DOMAIN" \
        -d "www.$DOMAIN"


    if [ $? -ne 0 ]; then

        echo
        echo -e "${RED}SSL certificate installation failed for $DOMAIN.${NC}"
        echo
        echo "Make sure:"
        echo
        echo "1. $DOMAIN points to this server."
        echo "2. www.$DOMAIN points to this server."
        echo "3. Port 80 is open."
        echo "4. No other service is using port 80."
        echo

        exit 1

    fi


    echo
    echo -e "${GREEN}SSL certificate for main domain installed successfully.${NC}"


    # ======================================================
    # SSL SUB DOMAIN
    # ======================================================

    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "=========================================="
        echo "Getting SSL certificate for Sub domain..."
        echo "=========================================="
        echo

        echo "Sub domain:"
        echo "$SUB_DOMAIN"
        echo


        certbot certonly \
            --standalone \
            --agree-tos \
            --register-unsafely-without-email \
            --non-interactive \
            -d "$SUB_DOMAIN"


        if [ $? -ne 0 ]; then

            echo
            echo -e "${RED}SSL certificate installation failed for $SUB_DOMAIN.${NC}"
            echo
            echo "Make sure:"
            echo
            echo "1. $SUB_DOMAIN points to this server."
            echo "2. Port 80 is open."
            echo "3. No other service is using port 80."
            echo

            exit 1

        fi


        echo
        echo -e "${GREEN}SSL certificate for Sub domain installed successfully.${NC}"

    fi


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
    # PROJECT
    # ======================================================

    cd "$APP_DIR"


    echo
    echo "Project files:"
    echo

    ls -la

    echo


    # ======================================================
    # CHECK APP.PY
    # ======================================================

    if [ ! -f "$APP_DIR/app.py" ]; then

        echo -e "${RED}ERROR: app.py not found.${NC}"

        exit 1

    fi


    echo -e "${GREEN}app.py found.${NC}"


    # ======================================================
    # CHECK TEL.PY
    # ======================================================

    echo
    echo "=========================================="
    echo "Checking tel.py..."
    echo "=========================================="


    if [ ! -f "$APP_DIR/tel.py" ]; then

        echo -e "${RED}ERROR: tel.py not found.${NC}"

        exit 1

    fi


    echo -e "${GREEN}tel.py found.${NC}"


    # ======================================================
    # CHECK BACKUP.PY
    # ======================================================

    echo
    echo "=========================================="
    echo "Checking backup.py..."
    echo "=========================================="


    if [ ! -f "$BACKUP_SCRIPT" ]; then

        echo -e "${RED}ERROR: backup.py not found.${NC}"
        echo
        echo "Expected:"
        echo "$BACKUP_SCRIPT"
        echo

        exit 1

    fi


    echo -e "${GREEN}backup.py found.${NC}"


    # ======================================================
    # CHECK TRADE.PY
    # ======================================================

    echo
    echo "=========================================="
    echo "Checking trade.py..."
    echo "=========================================="


    if [ ! -f "$TRADE_SCRIPT" ]; then

        echo -e "${RED}ERROR: trade.py not found.${NC}"
        echo
        echo "Expected:"
        echo "$TRADE_SCRIPT"
        echo

        exit 1

    fi


    echo -e "${GREEN}trade.py found.${NC}"


    # ======================================================
    # CHECK CURRENCIES.JSON
    # ======================================================

    echo
    echo "=========================================="
    echo "Checking currencies.json..."
    echo "=========================================="


    if [ ! -f "$CURRENCIES_FILE" ]; then

        echo -e "${RED}ERROR: currencies.json not found.${NC}"
        echo
        echo "Expected:"
        echo "$CURRENCIES_FILE"
        echo

        exit 1

    fi


    echo -e "${GREEN}currencies.json found.${NC}"


    # ======================================================
    # CHECK SUB.PY
    # ======================================================

    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "=========================================="
        echo "Checking sub.py..."
        echo "=========================================="


        if [ ! -f "$APP_DIR/sub.py" ]; then

            echo -e "${RED}ERROR: sub.py not found.${NC}"
            echo
            echo "Sub installation was enabled."
            echo
            echo "Expected:"
            echo "$APP_DIR/sub.py"
            echo

            exit 1

        fi


        echo -e "${GREEN}sub.py found.${NC}"

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


    echo -e "${GREEN}Virtual environment created.${NC}"


    # ======================================================
    # PIP
    # ======================================================

    echo
    echo "Upgrading pip..."


    "$VENV/bin/python" -m pip install --upgrade pip


    if [ $? -ne 0 ]; then

        echo -e "${RED}pip upgrade failed.${NC}"

        exit 1

    fi


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


    echo -e "${GREEN}Python packages installed.${NC}"


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
    # TRADE SERVICE
    # ======================================================

    echo
    echo "=========================================="
    echo "Creating trade.service..."
    echo "=========================================="


    cat > "$TRADE_SERVICE" <<EOF
[Unit]
Description=Trade Telegram Bot Service
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=$APP_DIR
ExecStart=$VENV/bin/python $APP_DIR/trade.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF


    # ======================================================
    # SUB SERVICE
    # ======================================================

    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "=========================================="
        echo "Creating sub.service..."
        echo "=========================================="


        cat > "$SUB_SERVICE" <<EOF
[Unit]
Description=Sub Application Service
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV/bin"
ExecStart=$VENV/bin/gunicorn --workers 3 --bind unix:$APP_DIR/sub.sock sub:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    else

        rm -f "$SUB_SERVICE"

    fi


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
    systemctl enable trade


    if [ "$INSTALL_SUB" = "yes" ]; then

        systemctl enable sub

    fi


    # ======================================================
    # BACKUP CRON
    # ======================================================

    echo
    echo "=========================================="
    echo "Configuring backup cron..."
    echo "=========================================="


    crontab -l 2>/dev/null \
        | grep -v "$BACKUP_SCRIPT" \
        | grep -v "$TRADE_SCRIPT" \
        > /tmp/current_cron 2>/dev/null || true


    echo "0 0 * * * $VENV/bin/python $BACKUP_SCRIPT >> $BACKUP_LOG 2>&1" \
        >> /tmp/current_cron


    crontab /tmp/current_cron

    rm -f /tmp/current_cron


    echo
    echo -e "${GREEN}Backup cron installed.${NC}"

    echo
    echo "Backup schedule:"
    echo "Every day at 00:00"


    # ======================================================
    # NGINX CONFIGURATION
    # ======================================================

    echo
    echo "=========================================="
    echo "Creating Nginx configuration..."
    echo "=========================================="


    # ======================================================
    # MAIN DOMAIN HTTP
    # ======================================================

    cat > "$NGINX_CONFIG" <<EOF
# ==========================================================
# MAIN DOMAIN - HTTP
# ==========================================================

server {

    listen 80;

    server_name $DOMAIN www.$DOMAIN;

    return 301 https://\$host\$request_uri;
}


# ==========================================================
# MAIN DOMAIN - HTTPS
# ==========================================================

server {

    listen 443 ssl;

    server_name $DOMAIN www.$DOMAIN;


    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;

    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;


    ssl_protocols TLSv1.2 TLSv1.3;

    ssl_ciphers HIGH:!aNULL:!MD5;


    # ======================================================
    # EVERYTHING -> PEAK
    # ======================================================

    location / {

        include proxy_params;

        proxy_pass http://unix:$APP_DIR/peak.sock:;

    }

}

EOF


    # ======================================================
    # SUB DOMAIN
    # ======================================================

    if [ "$INSTALL_SUB" = "yes" ]; then

        cat >> "$NGINX_CONFIG" <<EOF

# ==========================================================
# SUB DOMAIN - HTTP
# ==========================================================

server {

    listen 80;

    server_name $SUB_DOMAIN;

    return 301 https://\$host\$request_uri;
}


# ==========================================================
# SUB DOMAIN - HTTPS
# ==========================================================

server {

    listen 443 ssl;

    server_name $SUB_DOMAIN;


    ssl_certificate /etc/letsencrypt/live/$SUB_DOMAIN/fullchain.pem;

    ssl_certificate_key /etc/letsencrypt/live/$SUB_DOMAIN/privkey.pem;


    ssl_protocols TLSv1.2 TLSv1.3;

    ssl_ciphers HIGH:!aNULL:!MD5;


    # ======================================================
    # GX -> SUB
    # ======================================================

    location /gx/ {

        include proxy_params;

        proxy_pass http://unix:$APP_DIR/sub.sock:;

    }


    # ======================================================
    # EVERYTHING ELSE ON SUB DOMAIN -> PEAK
    # ======================================================

    location / {

        include proxy_params;

        proxy_pass http://unix:$APP_DIR/peak.sock:;

    }

}

EOF

    fi


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
        echo

        exit 1

    fi


    echo -e "${GREEN}Nginx configuration is valid.${NC}"


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
    # START TRADE
    # ======================================================

    echo
    echo "Starting trade..."


    systemctl restart trade

    sleep 2


    # ======================================================
    # START SUB
    # ======================================================

    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "Starting sub..."


        systemctl restart sub

        sleep 2

    fi


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
    # FINAL STATUS
    # ======================================================

    echo
    echo
    echo "=========================================="
    echo -e "${GREEN}INSTALLATION FINISHED${NC}"
    echo "=========================================="
    echo


    echo -e "${BLUE}Main Website:${NC}"
    echo "https://$DOMAIN"


    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo -e "${BLUE}Sub Website:${NC}"
        echo "https://$SUB_DOMAIN/gx/"

    fi


    echo
    echo -e "${BLUE}Application:${NC}"
    echo "$APP_DIR"


    echo
    echo -e "${BLUE}GitHub:${NC}"
    echo "$REPO"


    # ======================================================
    # ROUTING
    # ======================================================

    echo
    echo "=========================================="
    echo "ROUTING"
    echo "=========================================="


    echo
    echo "https://$DOMAIN/*"
    echo "        -> peak.sock"


    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "https://$SUB_DOMAIN/gx/*"
        echo "        -> sub.sock"

        echo
        echo "https://$SUB_DOMAIN/*"
        echo "        -> peak.sock"

    fi


    # ======================================================
    # SSL
    # ======================================================

    echo
    echo "=========================================="
    echo "SSL"
    echo "=========================================="


    echo
    echo "Main SSL certificate:"
    echo "/etc/letsencrypt/live/$DOMAIN/"


    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "Sub SSL certificate:"
        echo "/etc/letsencrypt/live/$SUB_DOMAIN/"

    fi


    echo
    echo "Auto renewal:"
    echo "ENABLED"


    echo
    echo "Check renewal timer:"
    echo "systemctl status certbot.timer"


    echo
    echo "Manual renewal:"
    echo "certbot renew"


    echo
    echo "Test renewal:"
    echo "certbot renew --dry-run"


    # ======================================================
    # SERVICES
    # ======================================================

    echo
    echo "=========================================="
    echo "SERVICES"
    echo "=========================================="


    echo
    echo "Peak:"
    echo "systemctl status peak"


    echo
    echo "Bot:"
    echo "systemctl status bot"


    echo
    echo "Trade:"
    echo "systemctl status trade"


    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "Sub:"
        echo "systemctl status sub"

    fi


    # ======================================================
    # LOGS
    # ======================================================

    echo
    echo "=========================================="
    echo "LOGS"
    echo "=========================================="


    echo
    echo "Peak:"
    echo "journalctl -u peak -f"


    echo
    echo "Bot:"
    echo "journalctl -u bot -f"


    echo
    echo "Trade:"
    echo "journalctl -u trade -f"


    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "Sub:"
        echo "journalctl -u sub -f"

    fi


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


    read -p "Enter main domain: " DOMAIN

    DOMAIN=$(clean_domain "$DOMAIN")


    if ! validate_domain "$DOMAIN"; then

        echo
        echo -e "${RED}Invalid domain.${NC}"
        echo

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
    echo "  trade.service"
    echo "  sub.service"
    echo "  Nginx configuration"
    echo "  SSL certificate for $DOMAIN"
    echo "  Backup cron job"
    echo "  Backup log"
    echo "  Trade log"
    echo


    read -p "Do you also want to remove a Sub domain SSL? [y/N]: " REMOVE_SUB


    REMOVE_SUB_SSL="no"
    REMOVE_SUB_DOMAIN=""


    if [[ "$REMOVE_SUB" =~ ^[Yy]$ ]]; then

        REMOVE_SUB_SSL="yes"

        read -p "Enter Sub domain: " REMOVE_SUB_DOMAIN

        REMOVE_SUB_DOMAIN=$(clean_domain "$REMOVE_SUB_DOMAIN")


        if [ -z "$REMOVE_SUB_DOMAIN" ]; then

            echo -e "${RED}Sub domain cannot be empty.${NC}"

            exit 1

        fi

        echo
        echo "SSL certificate for:"
        echo "$REMOVE_SUB_DOMAIN"
        echo "will also be removed."

    fi


    echo
    read -p "Type YES to continue: " CONFIRM


    if [ "$CONFIRM" != "YES" ]; then

        echo
        echo "Cancelled."

        exit 0

    fi


    # ======================================================
    # STOP SERVICES
    # ======================================================

    echo
    echo "Stopping services..."


    systemctl stop peak 2>/dev/null || true
    systemctl stop bot 2>/dev/null || true
    systemctl stop trade 2>/dev/null || true
    systemctl stop sub 2>/dev/null || true


    # ======================================================
    # DISABLE SERVICES
    # ======================================================

    echo
    echo "Disabling services..."


    systemctl disable peak 2>/dev/null || true
    systemctl disable bot 2>/dev/null || true
    systemctl disable trade 2>/dev/null || true
    systemctl disable sub 2>/dev/null || true


    # ======================================================
    # REMOVE SYSTEMD FILES
    # ======================================================

    echo
    echo "Removing systemd files..."


    rm -f "$PEAK_SERVICE"
    rm -f "$BOT_SERVICE"
    rm -f "$TRADE_SERVICE"
    rm -f "$SUB_SERVICE"


    systemctl daemon-reload

    systemctl reset-failed 2>/dev/null || true


    # ======================================================
    # REMOVE CRON
    # ======================================================

    echo
    echo "Removing cron jobs..."


    crontab -l 2>/dev/null \
        | grep -v "$BACKUP_SCRIPT" \
        | grep -v "$TRADE_SCRIPT" \
        > /tmp/current_cron 2>/dev/null || true


    crontab /tmp/current_cron 2>/dev/null || true

    rm -f /tmp/current_cron


    # ======================================================
    # REMOVE LOGS
    # ======================================================

    echo
    echo "Removing logs..."


    rm -f "$BACKUP_LOG"
    rm -f "$TRADE_LOG"


    # ======================================================
    # REMOVE NGINX CONFIG
    # ======================================================

    echo
    echo "Removing Nginx configuration..."


    rm -f /etc/nginx/sites-enabled/nginx.conf
    rm -f /etc/nginx/sites-available/nginx.conf


    # ======================================================
    # REMOVE APPLICATION
    # ======================================================

    echo
    echo "Removing application..."


    rm -rf "$APP_DIR"


    # ======================================================
    # REMOVE MAIN SSL
    # ======================================================

    echo
    echo "Removing main SSL certificate..."


    certbot delete \
        --cert-name "$DOMAIN" \
        --non-interactive 2>/dev/null || true


    # ======================================================
    # REMOVE SUB SSL
    # ======================================================

    if [ "$REMOVE_SUB_SSL" = "yes" ]; then

        echo
        echo "Removing Sub SSL certificate..."


        certbot delete \
            --cert-name "$REMOVE_SUB_DOMAIN" \
            --non-interactive 2>/dev/null || true

    fi


    # ======================================================
    # RESTART NGINX
    # ======================================================

    if nginx -t >/dev/null 2>&1; then

        systemctl restart nginx

    fi


    # ======================================================
    # DONE
    # ======================================================

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
