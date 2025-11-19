#!/bin/bash
# Startup script for PyUtils Web Browser

echo "=================================================="
echo "🔧 PyUtils Tool Browser"
echo "=================================================="
echo ""
echo "Starting web interface..."
echo "Navigate to: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================================="
echo ""

cd "$(dirname "$0")"
python app.py
