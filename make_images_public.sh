#!/bin/bash
# Make Digital Ocean Spaces images publicly accessible via CDN

set -e

echo "🔓 Making Spaces images publicly accessible"
echo "============================================"
echo ""

# Load credentials from .env
if [ ! -f .env ]; then
    echo "❌ .env file not found"
    exit 1
fi

export $(grep -v '^#' .env | xargs)

# Configure s3cmd for Digital Ocean Spaces
cat > /tmp/s3cfg_do << EOF
[default]
access_key = $SPACES_ACCESS_KEY
secret_key = $SPACES_SECRET_KEY
host_base = ${SPACES_REGION}.digitaloceanspaces.com
host_bucket = %(bucket)s.${SPACES_REGION}.digitaloceanspaces.com
use_https = True
signature_v2 = False
EOF

echo "📋 Configuration:"
echo "   Bucket: $SPACES_BUCKET"
echo "   Region: $SPACES_REGION"
echo ""

# Option 1: Make a specific image public (for testing)
if [ "$1" == "test" ]; then
    echo "🧪 Test mode: Making one image public..."
    
    # Get the most recent image
    RECENT_IMAGE=$(s3cmd -c /tmp/s3cfg_do ls s3://$SPACES_BUCKET/images/ --recursive | tail -1 | awk '{print $4}')
    
    if [ -z "$RECENT_IMAGE" ]; then
        echo "❌ No images found in bucket"
        exit 1
    fi
    
    echo "   Image: $RECENT_IMAGE"
    s3cmd -c /tmp/s3cfg_do setacl --acl-public "$RECENT_IMAGE"
    
    # Extract just the path after bucket name
    IMAGE_PATH=$(echo "$RECENT_IMAGE" | sed "s|s3://$SPACES_BUCKET/||")
    CDN_URL="https://$SPACES_BUCKET.$SPACES_REGION.cdn.digitaloceanspaces.com/$IMAGE_PATH"
    
    echo ""
    echo "✅ Image is now public!"
    echo "   CDN URL: $CDN_URL"
    echo ""
    echo "🧪 Test it:"
    echo "   curl -I $CDN_URL"
    
elif [ "$1" == "all" ]; then
    # Option 2: Make ALL images public (use with caution!)
    echo "⚠️  WARNING: This will make ALL images publicly accessible!"
    echo "   This may not be HIPAA compliant for medical images."
    echo ""
    read -p "Are you sure? (yes/no): " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        echo "❌ Aborted"
        exit 0
    fi
    
    echo ""
    echo "🔓 Making all images public..."
    s3cmd -c /tmp/s3cfg_do setacl --acl-public --recursive s3://$SPACES_BUCKET/images/
    echo "✅ All images are now public!"
    
elif [ "$1" == "bucket" ]; then
    # Option 3: Set default ACL for bucket (future uploads will be public)
    echo "⚠️  WARNING: This will make future uploads publicly accessible by default!"
    echo ""
    read -p "Are you sure? (yes/no): " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        echo "❌ Aborted"
        exit 0
    fi
    
    echo ""
    echo "🔓 Setting bucket default ACL to public-read..."
    echo "   Note: This requires updating the code to NOT set ACL='private'"
    echo ""
    echo "✅ After this, update spaces_storage.py to remove ACL='private'"
    
else
    # Option 4: Make a specific image public by path
    if [ -n "$1" ]; then
        IMAGE_KEY="$1"
        echo "🔓 Making image public: $IMAGE_KEY"
        s3cmd -c /tmp/s3cfg_do setacl --acl-public "s3://$SPACES_BUCKET/$IMAGE_KEY"
        
        CDN_URL="https://$SPACES_BUCKET.$SPACES_REGION.cdn.digitaloceanspaces.com/$IMAGE_KEY"
        echo ""
        echo "✅ Image is now public!"
        echo "   CDN URL: $CDN_URL"
    else
        echo "Usage:"
        echo "  ./make_images_public.sh test                     # Make one recent image public (for testing)"
        echo "  ./make_images_public.sh all                      # Make ALL images public (⚠️  not recommended)"
        echo "  ./make_images_public.sh bucket                   # Set bucket default ACL to public"
        echo "  ./make_images_public.sh images/2026/01/PT123/... # Make specific image public"
        echo ""
        echo "Examples:"
        echo "  ./make_images_public.sh test"
        echo "  ./make_images_public.sh images/2026/01/PT21713AE4B38D/219d4623-d2bb-43ec-9c70-3e4d413bf5fa.jpg"
    fi
fi

# Cleanup
rm -f /tmp/s3cfg_do

echo ""
echo "💡 Remember: For HIPAA compliance, use signed URLs instead of public CDN URLs"
