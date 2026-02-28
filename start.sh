#!/bin/bash
echo "Installing dependencies..."
pip3 install -r requirements.txt
echo "Starting NBA 2K26 Tendency Generator..."
python3 app.py
