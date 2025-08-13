#!/bin/bash
# Build script for Render

echo "🚀 Building Yemen Net Bot..."

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p data logs

# Set permissions
chmod +x main.py run_bot.py

echo "✅ Build completed successfully!"