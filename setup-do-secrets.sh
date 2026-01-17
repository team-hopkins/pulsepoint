#!/bin/bash
# Script to set up Digital Ocean App Platform with secrets from .env file

set -e

echo "🔐 Digital Ocean App Platform Setup"
echo "===================================="
echo ""

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl CLI not found. Installing..."
    echo ""
    echo "Please install doctl first:"
    echo "  macOS: brew install doctl"
    echo "  Or visit: https://docs.digitalocean.com/reference/doctl/how-to/install/"
    exit 1
fi

# Check if authenticated
if ! doctl account get &> /dev/null; then
    echo "🔐 Authenticating with Digital Ocean..."
    echo "You'll need your API token from: https://cloud.digitalocean.com/account/api/tokens"
    doctl auth init
fi

echo "✅ Authenticated with Digital Ocean"
echo ""

# Load environment variables
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    exit 1
fi

echo "📋 Loading secrets from .env file..."
echo ""

# Export all variables from .env
set -a
source .env
set +a

# App configuration
APP_NAME="pulsepoint-medical-ai"
REGION="nyc3"  # New York datacenter

echo "App Configuration:"
echo "  Name: $APP_NAME"
echo "  Region: $REGION"
echo ""

# Create app spec file with secrets
cat > app-spec.yaml << EOF
name: ${APP_NAME}
region: ${REGION}

services:
  - name: api
    dockerfile_path: Dockerfile
    source_dir: /

    # Build from GitHub (you'll configure this in the dashboard)
    # github:
    #   repo: your-username/your-repo
    #   branch: main
    #   deploy_on_push: true

    # Environment variables (encrypted secrets)
    envs:
      - key: OPENAI_API_KEY
        value: ${OPENAI_API_KEY}
        scope: RUN_TIME
        type: SECRET

      - key: ANTHROPIC_API_KEY
        value: ${ANTHROPIC_API_KEY}
        scope: RUN_TIME
        type: SECRET

      - key: GOOGLE_API_KEY
        value: ${GOOGLE_API_KEY}
        scope: RUN_TIME
        type: SECRET

      - key: ARIZE_API_KEY
        value: ${ARIZE_API_KEY}
        scope: RUN_TIME
        type: SECRET

      - key: ARIZE_SPACE_KEY
        value: ${ARIZE_SPACE_KEY}
        scope: RUN_TIME
        type: SECRET

      - key: PHOENIX_API_KEY
        value: ${PHOENIX_API_KEY}
        scope: RUN_TIME
        type: SECRET

      - key: PHOENIX_COLLECTOR_ENDPOINT
        value: ${PHOENIX_COLLECTOR_ENDPOINT}
        scope: RUN_TIME

      - key: MONGODB_URI
        value: ${MONGODB_URI}
        scope: RUN_TIME
        type: SECRET

      - key: MONGODB_DB_NAME
        value: ${MONGODB_DB_NAME:-carepoint_medical}
        scope: RUN_TIME

      - key: SPACES_ACCESS_KEY
        value: ${SPACES_ACCESS_KEY}
        scope: RUN_TIME
        type: SECRET

      - key: SPACES_SECRET_KEY
        value: ${SPACES_SECRET_KEY}
        scope: RUN_TIME
        type: SECRET

      - key: SPACES_REGION
        value: ${SPACES_REGION}
        scope: RUN_TIME

      - key: SPACES_BUCKET
        value: ${SPACES_BUCKET}
        scope: RUN_TIME

      - key: PROJECT_NAME
        value: ${PROJECT_NAME}
        scope: RUN_TIME

      - key: ENVIRONMENT
        value: production
        scope: RUN_TIME

    # Health check
    health_check:
      http_path: /health
      initial_delay_seconds: 40
      period_seconds: 30
      timeout_seconds: 10
      success_threshold: 1
      failure_threshold: 3

    # HTTP configuration
    http_port: 8000

    # Instance size
    instance_count: 1
    instance_size_slug: professional-xs  # \$12/month, 1 vCPU, 2GB RAM

    # Auto-deploy
    routes:
      - path: /
EOF

echo "✅ Created app-spec.yaml with encrypted secrets"
echo ""

echo "📤 Next steps:"
echo ""
echo "Option 1: Create app using doctl CLI (Recommended)"
echo "  1. First, push your code to GitHub"
echo "  2. Create a Container Registry:"
echo "     doctl registry create pulsepoint-registry"
echo "  3. Build and push Docker image:"
echo "     ./deploy.sh"
echo "  4. Create the app:"
echo "     doctl apps create --spec app-spec.yaml"
echo ""
echo "Option 2: Create app via Dashboard (Easier for first time)"
echo "  1. Go to: https://cloud.digitalocean.com/apps/new"
echo "  2. Choose 'DigitalOcean Container Registry'"
echo "  3. I'll help you upload the image next"
echo ""

read -p "Do you want to create the app now via CLI? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Creating Container Registry..."

    # Check if registry exists
    if doctl registry get 2>/dev/null; then
        echo "✅ Registry already exists"
    else
        echo "Creating new registry..."
        doctl registry create pulsepoint-registry
        echo "✅ Registry created"
    fi

    echo ""
    echo "Now run: ./deploy.sh to build and push your Docker image"
    echo "Then run this script again to create the app"
else
    echo ""
    echo "📋 app-spec.yaml has been created with all your secrets"
    echo "You can now:"
    echo "  1. Create app via dashboard: https://cloud.digitalocean.com/apps/new"
    echo "  2. Or run: doctl apps create --spec app-spec.yaml"
fi
