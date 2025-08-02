#!/bin/bash

echo "🖥️ WhatsApp ColorBerry Display Launcher"
echo "======================================"

# Verificar si hay pantalla disponible
if [ -z "$DISPLAY" ]; then
    echo "🔧 Setting up display environment for ColorBerry..."
    export DISPLAY=:0
fi

# Verificar que el servidor esté funcionando
echo "🔍 Checking WhatsApp server status..."
if ! curl -s http://localhost:3333/status > /dev/null; then
    echo "❌ WhatsApp server not running, starting it..."
    sudo systemctl start whatsapp-server.service
    sleep 5
fi

# Verificar estado de autenticación
AUTH_STATUS=$(curl -s http://localhost:3333/status | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data['authenticated'])
except:
    print('false')
")

echo "🔐 Authentication status: $AUTH_STATUS"

if [ "$AUTH_STATUS" = "False" ]; then
    echo "⚠️ WhatsApp needs authentication first"
    echo "📱 Please authenticate using: python3 show_qr.py"
    echo "🌐 Or visit: http://localhost:3333 in browser"
    echo ""
    echo "Would you like to continue anyway? (y/n)"
    read -n 1 answer
    echo ""
    if [ "$answer" != "y" ] && [ "$answer" != "Y" ]; then
        echo "❌ Cancelled"
        exit 1
    fi
fi

echo "🚀 Launching WhatsApp on ColorBerry display..."
echo "📋 Controls:"
echo "   - Arrow keys: Navigate menus"
echo "   - Enter: Select/Send"
echo "   - ESC: Back/Exit"
echo "   - Space: Special actions"
echo ""

# Lanzar WhatsApp con interfaz gráfica
DISPLAY=:0 python3 whatsapp.py
