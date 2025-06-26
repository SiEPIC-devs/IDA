#!/bin/bash

echo "Setting up Python virtual environment..."

# Create virtual environment
python3 -m venv venv

# Activate venv (Linux/Mac)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Upgrade pip and install requirements
pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete! Virtual environment is active."
echo "To activate later: source venv/bin/activate (Linux)"