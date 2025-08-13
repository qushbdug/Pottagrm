#!/bin/bash
# Build script for Render

echo "🚀 Building Yemen Net Bot..."

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data logs

# Set permissions
echo "🔐 Setting permissions..."
chmod +x main.py run_bot.py

echo "✅ Build completed successfully!"