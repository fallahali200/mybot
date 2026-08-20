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


    # ======================================================
    # SUB APPLICATION
    # ======================================================

    echo
    echo "=========================================="
    echo "SUB APPLICATION"
    echo "=========================================="
    echo

    echo "Do you want to install the sub application"
    echo "on this server?"
    echo
    echo "If YES:"
    echo "  /gx/ -> sub.sock"
    echo
    echo "If NO:"
    echo "  /gx/ will not be configured."
    echo

    read -p "Install sub application on this server? [y/N]: " INSTALL_SUB


    if [[ "$INSTALL_SUB" =~ ^[Yy]$ ]]; then

        INSTALL_SUB="yes"

        echo
        echo -e "${GREEN}Sub application: ENABLED${NC}"

    else

        INSTALL_SUB="no"

        echo
        echo -e "${YELLOW}Sub application: DISABLED${NC}"

    fi


    echo
    echo -e "${GREEN}Domain:${NC} $DOMAIN"
    echo -e "${GREEN}GitHub:${NC} $REPO"
    echo -e "${GREEN}Sub application:${NC} $INSTALL_SUB"
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
        echo
        echo "1. Domain points to this server."
        echo "2. Port 80 is open."
        echo "3. No other service is using port 80."
        echo

        exit 1

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
    # CHECK PROJECT
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

        echo -e "${RED}ERROR: backup.py not found in GitHub repository.${NC}"
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

        echo -e "${RED}ERROR: trade.py not found in GitHub repository.${NC}"
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

        echo -e "${RED}ERROR: currencies.json not found in GitHub repository.${NC}"
        echo
        echo "Expected:"
        echo "$CURRENCIES_FILE"
        echo

        exit 1

    fi


    echo -e "${GREEN}currencies.json found.${NC}"


    # ======================================================
    # CHECK SUB APPLICATION
    # ======================================================

    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "=========================================="
        echo "Checking sub application..."
        echo "=========================================="


        # --------------------------------------------------
        # CHANGE THIS FILE IF YOUR SUB APP USES ANOTHER
        # PYTHON FILE.
        # --------------------------------------------------

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


    # ======================================================
    # BACKUP EVERY DAY 00:00
    # ======================================================

    echo "0 0 * * * $VENV/bin/python $BACKUP_SCRIPT >> $BACKUP_LOG 2>&1" \
        >> /tmp/current_cron


    # ======================================================
    # INSTALL CRON
    # ======================================================

    crontab /tmp/current_cron

    rm -f /tmp/current_cron


    echo
    echo -e "${GREEN}Backup cron installed.${NC}"

    echo
    echo "Backup schedule:"
    echo "Every day at 00:00"

    echo
    echo "Backup command:"
    echo "$VENV/bin/python $BACKUP_SCRIPT"

    echo
    echo "Backup log:"
    echo "$BACKUP_LOG"


    # ======================================================
    # NGINX CONFIG
    # ======================================================

    echo
    echo "=========================================="
    echo "Creating Nginx configuration..."
    echo "=========================================="


    cat > "$NGINX_CONFIG" <<EOF
# ==========================================================
# HTTP -> HTTPS
# ==========================================================

server {

    listen 80;

    server_name $DOMAIN www.$DOMAIN;

    return 301 https://\$host\$request_uri;
}


# ==========================================================
# HTTPS
# ==========================================================

server {

    listen 443 ssl;

    server_name $DOMAIN www.$DOMAIN;


    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;

    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;


    ssl_protocols TLSv1.2 TLSv1.3;

    ssl_ciphers HIGH:!aNULL:!MD5;


    # ======================================================
    # GX APPLICATION
    # ======================================================

EOF


    # ======================================================
    # ADD GX ONLY IF SUB IS INSTALLED
    # ======================================================

    if [ "$INSTALL_SUB" = "yes" ]; then

        cat >> "$NGINX_CONFIG" <<EOF

    location /gx/ {

        include proxy_params;

        proxy_pass http://unix:$APP_DIR/sub.sock;

    }

EOF

    fi


    # ======================================================
    # MAIN APPLICATION
    # ======================================================

    cat >> "$NGINX_CONFIG" <<EOF

    # ======================================================
    # MAIN APPLICATION
    # ======================================================

    location / {

        include proxy_params;

        proxy_pass http://unix:$APP_DIR/peak.sock;

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


    # ======================================================
    # WEBSITE
    # ======================================================

    echo -e "${BLUE}Website:${NC}"

    echo "https://$DOMAIN"


    # ======================================================
    # APPLICATION
    # ======================================================

    echo
    echo -e "${BLUE}Application:${NC}"

    echo "$APP_DIR"


    # ======================================================
    # GITHUB
    # ======================================================

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
    echo "/ -> $APP_DIR/peak.sock"


    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "/gx/ -> $APP_DIR/sub.sock"

        echo
        echo -e "${GREEN}Sub application installed and enabled.${NC}"

    else

        echo
        echo "/gx/ -> NOT CONFIGURED"

        echo
        echo -e "${YELLOW}Sub application was not installed.${NC}"

    fi


    # ======================================================
    # BACKUP
    # ======================================================

    echo
    echo -e "${BLUE}Backup:${NC}"

    echo "$BACKUP_SCRIPT"


    echo
    echo -e "${BLUE}Backup schedule:${NC}"

    echo "Every day at 00:00"


    echo
    echo -e "${BLUE}Backup log:${NC}"

    echo "$BACKUP_LOG"


    # ======================================================
    # TRADE
    # ======================================================

    echo
    echo -e "${BLUE}Trade:${NC}"

    echo "$TRADE_SCRIPT"


    echo
    echo -e "${BLUE}Trade service:${NC}"

    echo "trade.service"


    echo
    echo -e "${BLUE}Trade mode:${NC}"

    echo "Always running"


    echo
    echo -e "${BLUE}Trade log:${NC}"

    echo "journalctl -u trade -f"


    # ======================================================
    # PEAK STATUS
    # ======================================================

    echo
    echo "=========================================="
    echo "PEAK STATUS"
    echo "=========================================="


    systemctl --no-pager status peak || true


    # ======================================================
    # BOT STATUS
    # ======================================================

    echo
    echo "=========================================="
    echo "BOT STATUS"
    echo "=========================================="


    systemctl --no-pager status bot || true


    # ======================================================
    # TRADE STATUS
    # ======================================================

    echo
    echo "=========================================="
    echo "TRADE STATUS"
    echo "=========================================="


    systemctl --no-pager status trade || true


    # ======================================================
    # SUB STATUS
    # ======================================================

    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "=========================================="
        echo "SUB STATUS"
        echo "=========================================="


        systemctl --no-pager status sub || true

    fi


    # ======================================================
    # NGINX STATUS
    # ======================================================

    echo
    echo "=========================================="
    echo "NGINX STATUS"
    echo "=========================================="


    systemctl --no-pager status nginx || true


    # ======================================================
    # BACKUP CRON
    # ======================================================

    echo
    echo "=========================================="
    echo "BACKUP CRON"
    echo "=========================================="


    crontab -l 2>/dev/null | grep "$BACKUP_SCRIPT" || true


    # ======================================================
    # TRADE SERVICE CHECK
    # ======================================================

    echo
    echo "=========================================="
    echo "TRADE SERVICE"
    echo "=========================================="


    systemctl is-enabled trade 2>/dev/null || true

    systemctl is-active trade 2>/dev/null || true


    # ======================================================
    # SUB SERVICE CHECK
    # ======================================================

    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "=========================================="
        echo "SUB SERVICE"
        echo "=========================================="


        systemctl is-enabled sub 2>/dev/null || true

        systemctl is-active sub 2>/dev/null || true

    fi


    # ======================================================
    # COMMANDS
    # ======================================================

    echo
    echo "=========================================="
    echo "USEFUL COMMANDS"
    echo "=========================================="


    echo
    echo "Trade status:"
    echo "systemctl status trade"


    echo
    echo "Trade logs:"
    echo "journalctl -u trade -f"


    echo
    echo "Bot status:"
    echo "systemctl status bot"


    echo
    echo "Bot logs:"
    echo "journalctl -u bot -f"


    echo
    echo "Peak status:"
    echo "systemctl status peak"


    echo
    echo "Peak logs:"
    echo "journalctl -u peak -f"


    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "Sub status:"
        echo "systemctl status sub"


        echo
        echo "Sub logs:"
        echo "journalctl -u sub -f"


        echo
        echo "Restart sub:"
        echo "systemctl restart sub"

    fi


    echo
    echo "Restart trade:"
    echo "systemctl restart trade"


    echo
    echo "Restart bot:"
    echo "systemctl restart bot"


    echo
    echo "Restart peak:"
    echo "systemctl restart peak"


    echo
    echo "Restart nginx:"
    echo "systemctl restart nginx"


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
    echo "  trade.service"
    echo "  sub.service"
    echo "  Nginx configuration"
    echo "  SSL certificate for $DOMAIN"
    echo "  Backup cron job"
    echo "  Backup log"
    echo "  Trade log"
    echo


    read -p "Type YES to continue: " CONFIRM


    if [ "$CONFIRM" != "YES" ]; then

        echo
        echo "Cancelled."

        exit 0

    fi


    # ======================================================
    # STOP PEAK
    # ======================================================

    echo
    echo "Stopping peak..."

    systemctl stop peak 2>/dev/null || true


    # ======================================================
    # STOP BOT
    # ======================================================

    echo "Stopping bot..."

    systemctl stop bot 2>/dev/null || true


    # ======================================================
    # STOP TRADE
    # ======================================================

    echo "Stopping trade..."

    systemctl stop trade 2>/dev/null || true


    # ======================================================
    # STOP SUB
    # ======================================================

    echo "Stopping sub..."

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
    echo "Removing backup and trade cron jobs..."


    crontab -l 2>/dev/null \
        | grep -v "$BACKUP_SCRIPT" \
        | grep -v "$TRADE_SCRIPT" \
        > /tmp/current_cron 2>/dev/null || true


    crontab /tmp/current_cron 2>/dev/null || true


    rm -f /tmp/current_cron


    # ======================================================
    # REMOVE BACKUP LOG
    # ======================================================

    echo
    echo "Removing backup log..."

    rm -f "$BACKUP_LOG"


    # ======================================================
    # REMOVE TRADE LOG
    # ======================================================

    echo
    echo "Removing trade log..."

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
    # REMOVE SSL
    # ======================================================

    echo
    echo "Removing SSL certificate..."


    certbot delete \
        --cert-name "$DOMAIN" \
        --non-interactive 2>/dev/null || true


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
