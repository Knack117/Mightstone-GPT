#!/bin/bash
# Quick setup script for Mightstone GPT

echo "🚀 Setting up Mightstone GPT..."

# Check Python version
python_version=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python $python_version detected (>= $required_version required)"
else
    echo "❌ Python $python_version detected. Requires Python >= $required_version"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
if command -v pip &> /dev/null; then
    pip install -r requirements.txt
elif command -v pip3 &> /dev/null; then
    pip3 install -r requirements.txt
else
    echo "❌ pip not found. Please install pip first."
    exit 1
fi

# Make scripts executable
chmod +x start.py
chmod +x test_api.py

echo "✅ Setup complete!"
echo ""
echo "🚀 To start the service:"
echo "   python start.py"
echo ""
echo "🧪 To test the API:"
echo "   python test_api.py"
echo ""
echo "📚 API will be available at http://localhost:8080"
echo "📖 Documentation at http://localhost:8080/docs"