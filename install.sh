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

NGINX_AVAILABLE="/etc/nginx/sites-available/bot.conf"
NGINX_ENABLED="/etc/nginx/sites-enabled/bot.conf"

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

    echo
    echo -e "${RED}Please run this script with sudo.${NC}"
    echo
    echo "Example:"
    echo "sudo bash install.sh"
    echo

    exit 1

fi


# ==========================================================
# FUNCTIONS
# ==========================================================

clean_domain() {

    local INPUT="$1"

    INPUT=$(echo "$INPUT" \
        | sed 's#^[[:space:]]*##' \
        | sed 's#[[:space:]]*$##' \
        | sed 's#^https://##' \
        | sed 's#^http://##' \
        | sed 's#/$##' \
        | tr -d '[:space:]')

    echo "$INPUT"

}


# ==========================================================
# DOMAIN VALIDATION
# ==========================================================

valid_domain() {

    local D="$1"

    if [ -z "$D" ]; then
        return 1
    fi

    if [[ "$D" == *"/"* ]]; then
        return 1
    fi

    if [[ "$D" == *":"* ]]; then
        return 1
    fi

    if [[ "$D" == *"@"* ]]; then
        return 1
    fi

    if [[ "$D" == *" "* ]]; then
        return 1
    fi

    if [[ ! "$D" =~ ^[a-zA-Z0-9.-]+$ ]]; then
        return 1
    fi

    return 0

}


# ==========================================================
# COMMAND CHECK
# ==========================================================

check_command() {

    local CMD="$1"

    if ! command -v "$CMD" >/dev/null 2>&1; then

        echo
        echo -e "${RED}Command not found: $CMD${NC}"
        echo

        exit 1

    fi

}


# ==========================================================
# DNS CHECK
# ==========================================================

check_dns() {

    local D="$1"

    echo
    echo "Checking DNS:"
    echo "$D"
    echo

    if getent hosts "$D" >/dev/null 2>&1; then

        echo -e "${GREEN}DNS resolves: $D${NC}"

    else

        echo -e "${YELLOW}WARNING: DNS does not resolve: $D${NC}"
        echo
        echo "Make sure this domain points to this server."
        echo

    fi

}


# ==========================================================
# INSTALL
# ==========================================================

install_app() {

    clear

    echo
    echo "=================================================="
    echo "              SERVER INSTALLER"
    echo "=================================================="
    echo


    # ======================================================
    # MAIN DOMAIN
    # ======================================================

    echo "Enter MAIN domain."
    echo
    echo "Example:"
    echo "alpha.carselect.sbs"
    echo

    read -r -p "Main domain: " DOMAIN

    DOMAIN=$(clean_domain "$DOMAIN")


    if ! valid_domain "$DOMAIN"; then

        echo
        echo -e "${RED}Invalid main domain:${NC}"
        echo "$DOMAIN"
        echo

        exit 1

    fi


    # ======================================================
    # SUB INSTALL
    # ======================================================

    echo
    echo "=================================================="
    echo "                 SUB APPLICATION"
    echo "=================================================="
    echo

    echo "Do you want to install the SUB application?"
    echo
    echo "If YES, you will enter a SECOND DOMAIN."
    echo
    echo "Example:"
    echo
    echo "Main domain:"
    echo "  alpha.carselect.sbs"
    echo
    echo "Second domain:"
    echo "  sub.carselect.sbs"
    echo
    echo "Routing:"
    echo
    echo "  alpha.carselect.sbs/*"
    echo "        -> peak.sock"
    echo
    echo "  sub.carselect.sbs/gx/*"
    echo "        -> sub.sock"
    echo
    echo "  sub.carselect.sbs/*"
    echo "        -> peak.sock"
    echo


    read -r -p "Install SUB application? [y/N]: " SUB_CONFIRM


    if [[ "$SUB_CONFIRM" =~ ^[Yy]$ ]]; then

        INSTALL_SUB="yes"

        echo
        echo "=================================================="
        echo "                 SECOND DOMAIN"
        echo "=================================================="
        echo

        read -r -p "Second domain: " SUB_DOMAIN

        SUB_DOMAIN=$(clean_domain "$SUB_DOMAIN")


        if ! valid_domain "$SUB_DOMAIN"; then

            echo
            echo -e "${RED}Invalid second domain:${NC}"
            echo "$SUB_DOMAIN"
            echo

            exit 1

        fi


        if [ "$DOMAIN" = "$SUB_DOMAIN" ]; then

            echo
            echo -e "${RED}Main domain and second domain cannot be the same.${NC}"
            echo

            exit 1

        fi


        echo
        echo -e "${GREEN}SUB application enabled.${NC}"

    else

        INSTALL_SUB="no"

        SUB_DOMAIN=""

        echo
        echo -e "${YELLOW}SUB application disabled.${NC}"

    fi


    # ======================================================
    # SUMMARY
    # ======================================================

    echo
    echo "=================================================="
    echo "              INSTALLATION SUMMARY"
    echo "=================================================="
    echo

    echo "Main domain:"
    echo "  $DOMAIN"

    echo

    if [ "$INSTALL_SUB" = "yes" ]; then

        echo "Second domain:"
        echo "  $SUB_DOMAIN"

        echo
        echo "Routing:"
        echo
        echo "  https://$DOMAIN/*"
        echo "      -> peak.sock"
        echo
        echo "  https://$SUB_DOMAIN/gx/*"
        echo "      -> sub.sock"
        echo
        echo "  https://$SUB_DOMAIN/*"
        echo "      -> peak.sock"

    else

        echo "Routing:"
        echo
        echo "  https://$DOMAIN/*"
        echo "      -> peak.sock"

    fi


    echo
    echo "SSL:"
    echo

    echo "  $DOMAIN"

    if [ "$INSTALL_SUB" = "yes" ]; then
        echo "  $SUB_DOMAIN"
    fi

    echo
    echo "IMPORTANT:"
    echo "No www domain will be requested."
    echo


    read -r -p "Continue installation? [y/N]: " CONFIRM


    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then

        echo
        echo "Installation cancelled."

        exit 0

    fi


    # ======================================================
    # DNS
    # ======================================================

    echo
    echo "=================================================="
    echo "                 DNS CHECK"
    echo "=================================================="

    check_dns "$DOMAIN"


    if [ "$INSTALL_SUB" = "yes" ]; then

        check_dns "$SUB_DOMAIN"

    fi


    echo
    read -r -p "Have DNS records been configured correctly? [y/N]: " DNS_CONFIRM


    if [[ ! "$DNS_CONFIRM" =~ ^[Yy]$ ]]; then

        echo
        echo "Please configure DNS first."
        echo

        exit 0

    fi


    # ======================================================
    # UPDATE
    # ======================================================

    echo
    echo "=================================================="
    echo "                 SYSTEM UPDATE"
    echo "=================================================="


    apt update

    if [ $? -ne 0 ]; then

        echo -e "${RED}apt update failed.${NC}"

        exit 1

    fi


    apt upgrade -y


    # ======================================================
    # PACKAGES
    # ======================================================

    echo
    echo "=================================================="
    echo "              INSTALLING PACKAGES"
    echo "=================================================="


    apt install -y \
        nginx \
        certbot \
        git \
        python3 \
        python3-venv \
        python3-pip \
        cron


    if [ $? -ne 0 ]; then

        echo -e "${RED}Package installation failed.${NC}"

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

    systemctl enable cron
    systemctl start cron


    # ======================================================
    # STOP NGINX
    # ======================================================

    echo
    echo "Stopping Nginx..."

    systemctl stop nginx 2>/dev/null || true


    # ======================================================
    # SSL - MAIN DOMAIN
    # ======================================================

    echo
    echo "=================================================="
    echo "             SSL MAIN DOMAIN"
    echo "=================================================="
    echo

    echo "Requesting certificate for:"
    echo "$DOMAIN"
    echo

    certbot certonly \
        --standalone \
        --agree-tos \
        --register-unsafely-without-email \
        --non-interactive \
        -d "$DOMAIN"


    if [ $? -ne 0 ]; then

        echo
        echo -e "${RED}SSL installation failed for:${NC}"
        echo "$DOMAIN"
        echo
        echo "Check DNS and port 80."
        echo

        exit 1

    fi


    echo
    echo -e "${GREEN}SSL installed for $DOMAIN${NC}"


    # ======================================================
    # SSL - SECOND DOMAIN
    # ======================================================

    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "=================================================="
        echo "             SSL SECOND DOMAIN"
        echo "=================================================="
        echo

        echo "Requesting certificate for:"
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
            echo -e "${RED}SSL installation failed for:${NC}"
            echo "$SUB_DOMAIN"
            echo
            echo "Check DNS and port 80."
            echo

            exit 1

        fi


        echo
        echo -e "${GREEN}SSL installed for $SUB_DOMAIN${NC}"

    fi


    # ======================================================
    # APP DIRECTORY
    # ======================================================

    echo
    echo "=================================================="
    echo "             APPLICATION DIRECTORY"
    echo "=================================================="


    mkdir -p /var/www

    rm -rf "$APP_DIR"


    # ======================================================
    # CLONE
    # ======================================================

    echo
    echo "Cloning repository..."

    git clone "$REPO" "$APP_DIR"


    if [ $? -ne 0 ]; then

        echo
        echo -e "${RED}Git clone failed.${NC}"

        exit 1

    fi


    cd "$APP_DIR"


    # ======================================================
    # FILE CHECK
    # ======================================================

    echo
    echo "=================================================="
    echo "                 FILE CHECK"
    echo "=================================================="


    REQUIRED_FILES=(
        "app.py"
        "tel.py"
        "backup.py"
        "trade.py"
        "currencies.json"
    )


    for FILE in "${REQUIRED_FILES[@]}"
    do

        if [ ! -f "$APP_DIR/$FILE" ]; then

            echo
            echo -e "${RED}Missing file: $FILE${NC}"
            echo

            exit 1

        fi

        echo -e "${GREEN}$FILE found.${NC}"

    done


    if [ "$INSTALL_SUB" = "yes" ]; then

        if [ ! -f "$APP_DIR/sub.py" ]; then

            echo
            echo -e "${RED}Missing file: sub.py${NC}"
            echo

            exit 1

        fi

        echo -e "${GREEN}sub.py found.${NC}"

    fi


    # ======================================================
    # VENV
    # ======================================================

    echo
    echo "=================================================="
    echo "             PYTHON VIRTUAL ENV"
    echo "=================================================="


    rm -rf "$VENV"

    python3 -m venv "$VENV"


    if [ ! -f "$VENV/bin/python" ]; then

        echo
        echo -e "${RED}Virtual environment creation failed.${NC}"

        exit 1

    fi


    "$VENV/bin/python" -m pip install --upgrade pip


    if [ $? -ne 0 ]; then

        echo
        echo -e "${RED}pip upgrade failed.${NC}"

        exit 1

    fi


    # ======================================================
    # PYTHON PACKAGES
    # ======================================================

    echo
    echo "=================================================="
    echo "             PYTHON PACKAGES"
    echo "=================================================="


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
    echo "Creating peak.service..."


    cat > "$PEAK_SERVICE" <<EOF
[Unit]
Description=Peak Gunicorn Application
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV/bin"
Environment="PYTHONUNBUFFERED=1"

ExecStart=$VENV/bin/gunicorn \
    --workers 3 \
    --bind unix:$APP_DIR/peak.sock \
    app:app

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF


    # ======================================================
    # BOT SERVICE
    # ======================================================

    echo
    echo "Creating bot.service..."


    cat > "$BOT_SERVICE" <<EOF
[Unit]
Description=Telegram Bot
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV/bin"
Environment="PYTHONUNBUFFERED=1"

ExecStart=$VENV/bin/python $APP_DIR/tel.py

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF


    # ======================================================
    # TRADE SERVICE
    # ======================================================

    echo
    echo "Creating trade.service..."


    cat > "$TRADE_SERVICE" <<EOF
[Unit]
Description=Trade Telegram Bot
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV/bin"
Environment="PYTHONUNBUFFERED=1"

ExecStart=$VENV/bin/python $APP_DIR/trade.py

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF


    # ======================================================
    # SUB SERVICE
    # ======================================================

    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "Creating sub.service..."


        cat > "$SUB_SERVICE" <<EOF
[Unit]
Description=Sub Gunicorn Application
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV/bin"
Environment="PYTHONUNBUFFERED=1"

ExecStart=$VENV/bin/gunicorn \
    --workers 3 \
    --bind unix:$APP_DIR/sub.sock \
    sub:app

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    else

        rm -f "$SUB_SERVICE"

    fi


    # ======================================================
    # SYSTEMD
    # ======================================================

    echo
    echo "=================================================="
    echo "                 SYSTEMD"
    echo "=================================================="


    systemctl daemon-reload


    systemctl enable peak
    systemctl enable bot
    systemctl enable trade


    if [ "$INSTALL_SUB" = "yes" ]; then

        systemctl enable sub

    fi


    # ======================================================
    # CRON
    # ======================================================

    echo
    echo "=================================================="
    echo "                 BACKUP CRON"
    echo "=================================================="


    crontab -l 2>/dev/null \
        | grep -vF "$BACKUP_SCRIPT" \
        | grep -vF "$TRADE_SCRIPT" \
        > /tmp/bot_cron 2>/dev/null || true


    echo "0 0 * * * $VENV/bin/python $BACKUP_SCRIPT >> $BACKUP_LOG 2>&1" \
        >> /tmp/bot_cron


    crontab /tmp/bot_cron

    rm -f /tmp/bot_cron


    # ======================================================
    # NGINX CONFIG
    # ======================================================

    echo
    echo "=================================================="
    echo "                 NGINX"
    echo "=================================================="


    rm -f /etc/nginx/sites-enabled/default
    rm -f "$NGINX_ENABLED"


    # ======================================================
    # MAIN DOMAIN NGINX
    # ======================================================

    cat > "$NGINX_AVAILABLE" <<EOF
# ==========================================================
# MAIN DOMAIN HTTP
# ==========================================================

server {

    listen 80;

    server_name $DOMAIN;

    return 301 https://\$host\$request_uri;
}


# ==========================================================
# MAIN DOMAIN HTTPS
# ==========================================================

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

EOF


    # ======================================================
    # SECOND DOMAIN
    # ======================================================

    if [ "$INSTALL_SUB" = "yes" ]; then

        cat >> "$NGINX_AVAILABLE" <<EOF

}


# ==========================================================
# SECOND DOMAIN HTTP
# ==========================================================

server {

    listen 80;

    server_name $SUB_DOMAIN;

    return 301 https://\$host\$request_uri;
}


# ==========================================================
# SECOND DOMAIN HTTPS
# ==========================================================

server {

    listen 443 ssl;

    server_name $SUB_DOMAIN;


    ssl_certificate /etc/letsencrypt/live/$SUB_DOMAIN/fullchain.pem;

    ssl_certificate_key /etc/letsencrypt/live/$SUB_DOMAIN/privkey.pem;


    ssl_protocols TLSv1.2 TLSv1.3;


    # ======================================================
    # /gx/ -> SUB
    # ======================================================

    location /gx/ {

        include proxy_params;

        proxy_pass http://unix:$APP_DIR/sub.sock;

    }


    # ======================================================
    # EVERYTHING ELSE -> PEAK
    # ======================================================

    location / {

        include proxy_params;

        proxy_pass http://unix:$APP_DIR/peak.sock;

    }

}

EOF

    else

        cat >> "$NGINX_AVAILABLE" <<EOF

}

EOF

    fi


    # ======================================================
    # ENABLE NGINX
    # ======================================================

    ln -sf "$NGINX_AVAILABLE" "$NGINX_ENABLED"


    # ======================================================
    # PERMISSIONS
    # ======================================================

    echo
    echo "Setting permissions..."


    chown -R root:www-data "$APP_DIR"

    chmod 750 "$APP_DIR"


    # ======================================================
    # NGINX TEST
    # ======================================================

    echo
    echo "Testing Nginx..."


    nginx -t


    if [ $? -ne 0 ]; then

        echo
        echo -e "${RED}Nginx configuration test FAILED.${NC}"
        echo
        echo "Configuration:"
        echo "$NGINX_AVAILABLE"
        echo

        exit 1

    fi


    echo
    echo -e "${GREEN}Nginx configuration is valid.${NC}"


    # ======================================================
    # START SERVICES
    # ======================================================

    echo
    echo "Starting Peak..."

    systemctl restart peak

    sleep 2


    echo
    echo "Starting Bot..."

    systemctl restart bot

    sleep 2


    echo
    echo "Starting Trade..."

    systemctl restart trade

    sleep 2


    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "Starting Sub..."

        systemctl restart sub

        sleep 2

    fi


    # ======================================================
    # NGINX
    # ======================================================

    echo
    echo "Starting Nginx..."


    systemctl enable nginx

    systemctl restart nginx


    # ======================================================
    # CERTBOT TIMER
    # ======================================================

    echo
    echo "Enabling Certbot renewal..."


    systemctl enable certbot.timer
    systemctl start certbot.timer


    # ======================================================
    # FINAL RENEWAL TEST
    # ======================================================

    echo
    echo "Testing Certbot renewal..."


    certbot renew --dry-run || true


    # ======================================================
    # FINAL STATUS
    # ======================================================

    echo
    echo
    echo "=================================================="
    echo -e "${GREEN}             INSTALLATION COMPLETE${NC}"
    echo "=================================================="
    echo


    echo "MAIN DOMAIN:"
    echo
    echo "https://$DOMAIN"


    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "SECOND DOMAIN:"
        echo
        echo "https://$SUB_DOMAIN/gx/"

    fi


    echo
    echo "=================================================="
    echo "ROUTING"
    echo "=================================================="


    echo
    echo "$DOMAIN/*"
    echo "    -> peak.sock"


    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "$SUB_DOMAIN/gx/*"
        echo "    -> sub.sock"

        echo
        echo "$SUB_DOMAIN/*"
        echo "    -> peak.sock"

    fi


    echo
    echo "=================================================="
    echo "SSL"
    echo "=================================================="


    echo
    echo "Certificate:"
    echo "/etc/letsencrypt/live/$DOMAIN/"


    if [ "$INSTALL_SUB" = "yes" ]; then

        echo
        echo "Certificate:"
        echo "/etc/letsencrypt/live/$SUB_DOMAIN/"

    fi


    echo
    echo "IMPORTANT:"
    echo "No www certificate was requested."


    echo
    echo "=================================================="
    echo "SERVICES"
    echo "=================================================="


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


    echo
    echo "=================================================="
    echo "LOGS"
    echo "=================================================="


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
    echo "=================================================="
    echo -e "${GREEN}DONE${NC}"
    echo "=================================================="
    echo


    read -r -p "Press Enter to exit..."

}


# ==========================================================
# REMOVE
# ==========================================================

remove_app() {

    clear

    echo
    echo "=================================================="
    echo "              REMOVE EVERYTHING"
    echo "=================================================="
    echo


    read -r -p "Main domain: " DOMAIN

    DOMAIN=$(clean_domain "$DOMAIN")


    if ! valid_domain "$DOMAIN"; then

        echo
        echo -e "${RED}Invalid domain.${NC}"

        exit 1

    fi


    echo
    read -r -p "Do you also have a second domain? [y/N]: " REMOVE_SUB


    REMOVE_SUB_DOMAIN=""


    if [[ "$REMOVE_SUB" =~ ^[Yy]$ ]]; then

        read -r -p "Second domain: " REMOVE_SUB_DOMAIN

        REMOVE_SUB_DOMAIN=$(clean_domain "$REMOVE_SUB_DOMAIN")


        if ! valid_domain "$REMOVE_SUB_DOMAIN"; then

            echo
            echo -e "${RED}Invalid second domain.${NC}"

            exit 1

        fi

    fi


    echo
    echo "=================================================="
    echo "WARNING"
    echo "=================================================="
    echo

    echo "The following will be removed:"
    echo
    echo "$APP_DIR"
    echo "$PEAK_SERVICE"
    echo "$BOT_SERVICE"
    echo "$TRADE_SERVICE"
    echo "$SUB_SERVICE"
    echo "$NGINX_AVAILABLE"
    echo "$NGINX_ENABLED"
    echo "SSL: $DOMAIN"


    if [ -n "$REMOVE_SUB_DOMAIN" ]; then

        echo "SSL: $REMOVE_SUB_DOMAIN"

    fi


    echo
    echo "Backup cron"
    echo "Backup log"
    echo "Trade log"
    echo


    read -r -p "Type YES to continue: " CONFIRM


    if [ "$CONFIRM" != "YES" ]; then

        echo
        echo "Cancelled."

        exit 0

    fi


    # ======================================================
    # STOP
    # ======================================================

    echo
    echo "Stopping services..."


    systemctl stop peak 2>/dev/null || true
    systemctl stop bot 2>/dev/null || true
    systemctl stop trade 2>/dev/null || true
    systemctl stop sub 2>/dev/null || true


    # ======================================================
    # DISABLE
    # ======================================================

    echo
    echo "Disabling services..."


    systemctl disable peak 2>/dev/null || true
    systemctl disable bot 2>/dev/null || true
    systemctl disable trade 2>/dev/null || true
    systemctl disable sub 2>/dev/null || true


    # ======================================================
    # SYSTEMD FILES
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
    # CRON
    # ======================================================

    echo
    echo "Removing cron..."


    crontab -l 2>/dev/null \
        | grep -vF "$BACKUP_SCRIPT" \
        | grep -vF "$TRADE_SCRIPT" \
        > /tmp/bot_remove_cron 2>/dev/null || true


    crontab /tmp/bot_remove_cron 2>/dev/null || true

    rm -f /tmp/bot_remove_cron


    # ======================================================
    # LOGS
    # ======================================================

    echo
    echo "Removing logs..."


    rm -f "$BACKUP_LOG"
    rm -f "$TRADE_LOG"


    # ======================================================
    # NGINX
    # ======================================================

    echo
    echo "Removing Nginx configuration..."


    rm -f "$NGINX_ENABLED"
    rm -f "$NGINX_AVAILABLE"


    # ======================================================
    # APPLICATION
    # ======================================================

    echo
    echo "Removing application..."


    rm -rf "$APP_DIR"


    # ======================================================
    # MAIN SSL
    # ======================================================

    echo
    echo "Removing SSL:"
    echo "$DOMAIN"


    certbot delete \
        --cert-name "$DOMAIN" \
        --non-interactive \
        2>/dev/null || true


    # ======================================================
    # SECOND SSL
    # ======================================================

    if [ -n "$REMOVE_SUB_DOMAIN" ]; then

        echo
        echo "Removing SSL:"
        echo "$REMOVE_SUB_DOMAIN"


        certbot delete \
            --cert-name "$REMOVE_SUB_DOMAIN" \
            --non-interactive \
            2>/dev/null || true

    fi


    # ======================================================
    # NGINX TEST / RESTART
    # ======================================================

    if nginx -t >/dev/null 2>&1; then

        systemctl restart nginx

    fi


    # ======================================================
    # DONE
    # ======================================================

    echo
    echo "=================================================="
    echo -e "${GREEN}             REMOVAL COMPLETE${NC}"
    echo "=================================================="
    echo


    read -r -p "Press Enter to exit..."

}


# ==========================================================
# MENU
# ==========================================================

while true
do

    clear

    echo
    echo "=================================================="
    echo "                SERVER INSTALLER"
    echo "=================================================="
    echo

    echo "1) Install"
    echo "2) Remove everything"
    echo "3) Exit"
    echo

    read -r -p "Select option [1-3]: " OPTION


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
            echo

            sleep 2

            ;;

    esac

done
