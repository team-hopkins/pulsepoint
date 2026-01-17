#!/bin/bash

echo "🏥 CarePoint AI System - Quick Start Script"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "📝 IMPORTANT: Edit .env with your API keys before running!"
    echo "   - OPENAI_API_KEY"
    echo "   - ANTHROPIC_API_KEY"
    echo "   - GOOGLE_API_KEY"
    echo "   - ARIZE_SPACE_KEY"
    echo "   - ARIZE_API_KEY"
    echo ""
    read -p "Press Enter after you've configured .env..."
fi

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "🚀 To start the server, run:"
echo "   python main.py"
echo ""
echo "🧪 To test the API, run (in another terminal):"
echo "   python test_api.py"
echo ""
echo "📊 View monitoring dashboard at:"
echo "   https://app.arize.com"
echo ""
