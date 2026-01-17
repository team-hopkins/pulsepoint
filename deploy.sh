#!/bin/bash
# Deployment script for Digital Ocean

set -e

echo "🚀 Deployment Script for Digital Ocean"
echo "======================================"

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl CLI not found. Please install it:"
    echo "   macOS: brew install doctl"
    echo "   Or visit: https://docs.digitalocean.com/reference/doctl/how-to/install/"
    exit 1
fi

# Check if authenticated
if ! doctl account get &> /dev/null; then
    echo "🔐 Not authenticated. Please run:"
    echo "   doctl auth init"
    exit 1
fi

# Variables
REGISTRY="registry.digitalocean.com"
APP_NAME="pulsepoint-medical-ai"
IMAGE_NAME="pulsepoint-api"
REGISTRY_NAME="pulsepoint-registry"  # Default registry name

# Check if registry exists, create if not
echo ""
echo "🔍 Checking for Container Registry..."
if doctl registry get 2>/dev/null | grep -q "pulsepoint-registry"; then
    echo "✅ Registry 'pulsepoint-registry' found"
else
    echo "Creating new registry 'pulsepoint-registry'..."
    doctl registry create $REGISTRY_NAME
    echo "✅ Registry created"
fi

# Full image path
FULL_IMAGE_PATH="$REGISTRY/$REGISTRY_NAME/$IMAGE_NAME:latest"

echo ""
echo "🔐 Logging in to Digital Ocean Container Registry..."
doctl registry login

echo ""
echo "📦 Building and pushing Docker image for linux/amd64 platform..."
docker buildx build --platform linux/amd64 -t $FULL_IMAGE_PATH --push .

echo ""
echo "✅ Image pushed successfully!"
echo "   Image: $FULL_IMAGE_PATH"
echo ""
echo "Next steps:"
echo "1. Go to https://cloud.digitalocean.com/apps"
echo "2. Create a new app or update existing one"
echo "3. Select 'DigitalOcean Container Registry'"
echo "4. Choose the image: $FULL_IMAGE_PATH"
echo "5. Add environment variables from .env file"
echo "6. Deploy!"
