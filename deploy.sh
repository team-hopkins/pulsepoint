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
echo "🔍 Getting image digest..."
sleep 3  # Wait for registry to update

IMAGE_DIGEST=$(doctl registry repository list-tags $IMAGE_NAME --format Tag,Digest | grep "latest" | awk '{print $NF}')

if [ -z "$IMAGE_DIGEST" ] || [ "$IMAGE_DIGEST" == "0" ]; then
    echo "❌ Could not get image digest. Please check registry."
    exit 1
fi

echo "✅ Image digest: $IMAGE_DIGEST"

# Update app-spec.yaml with new digest (replace "tag: latest" with "digest: sha256:...")
echo "📝 Updating app-spec.yaml with new digest..."
sed -i.bak "s|tag: latest|digest: $IMAGE_DIGEST|g" app-spec.yaml
rm -f app-spec.yaml.bak
echo "✅ app-spec.yaml updated"

echo ""
echo "🚀 Deploying to Digital Ocean App Platform..."

# Check if app exists
APP_ID=$(doctl apps list --format ID,Spec.Name | grep "$APP_NAME" | awk '{print $1}')

if [ -z "$APP_ID" ]; then
    echo "📦 Creating new app: $APP_NAME"
    doctl apps create --spec app-spec.yaml
    echo "✅ App created successfully!"
else
    echo "🔄 Updating existing app: $APP_NAME (ID: $APP_ID)"
    doctl apps update $APP_ID --spec app-spec.yaml
    echo "✅ App updated successfully!"
fi

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📊 Check status:"
echo "   doctl apps list"
echo "   doctl apps get $APP_NAME"
echo ""
echo "📝 View logs:"
echo "   doctl apps logs $APP_NAME --type=run --follow"
echo ""
echo "🌐 View in browser:"
echo "   https://cloud.digitalocean.com/apps"
