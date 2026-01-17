"""Digital Ocean Spaces storage for medical images"""
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import os
import base64
import uuid
from typing import Optional, Tuple
from datetime import datetime
import mimetypes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class SpacesStorage:
    """Handle image storage in Digital Ocean Spaces (S3-compatible)"""
    
    def __init__(self):
        """Initialize Digital Ocean Spaces client"""
        self.spaces_key = os.getenv("SPACES_ACCESS_KEY")
        self.spaces_secret = os.getenv("SPACES_SECRET_KEY")
        self.spaces_region = os.getenv("SPACES_REGION", "sfo3")  # Default to SFO3
        self.spaces_bucket = os.getenv("SPACES_BUCKET", "testaid")
        self.spaces_endpoint = f"https://{self.spaces_region}.digitaloceanspaces.com"
        
        # Check if credentials are configured
        if not self.spaces_key or not self.spaces_secret:
            print("⚠️  Digital Ocean Spaces credentials not configured")
            print("   Set SPACES_ACCESS_KEY and SPACES_SECRET_KEY in .env")
            self.client = None
            return
        
        # Initialize boto3 client for Digital Ocean Spaces
        try:
            self.client = boto3.client(
                's3',
                region_name=self.spaces_region,
                endpoint_url=self.spaces_endpoint,
                aws_access_key_id=self.spaces_key,
                aws_secret_access_key=self.spaces_secret,
                config=Config(signature_version='s3v4')
            )
            print(f"✅ Connected to Digital Ocean Spaces: {self.spaces_bucket}")
        except Exception as e:
            print(f"❌ Failed to initialize Spaces client: {str(e)}")
            self.client = None
    
    def _decode_base64_image(self, base64_string: str) -> Tuple[bytes, str]:
        """
        Decode base64 image and determine content type
        
        Args:
            base64_string: Base64 encoded image (with or without data URI prefix)
            
        Returns:
            Tuple of (image_bytes, content_type)
        """
        # Remove data URI prefix if present
        if base64_string.startswith('data:'):
            # Format: data:image/jpeg;base64,<base64-string>
            header, encoded = base64_string.split(',', 1)
            content_type = header.split(';')[0].split(':')[1]
        else:
            encoded = base64_string
            content_type = "image/jpeg"  # Default
        
        # Decode base64
        image_bytes = base64.b64decode(encoded)
        
        return image_bytes, content_type
    
    def _generate_object_key(self, patient_id: str, content_type: str) -> str:
        """
        Generate unique object key for image storage
        
        Format: images/{year}/{month}/{patient_id}/{uuid}.{ext}
        
        Args:
            patient_id: Patient identifier
            content_type: MIME type (e.g., image/jpeg)
            
        Returns:
            Object key path
        """
        now = datetime.utcnow()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        
        # Get file extension from content type
        extension = mimetypes.guess_extension(content_type) or '.jpg'
        if extension == '.jpe':
            extension = '.jpg'
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())
        
        return f"images/{year}/{month}/{patient_id}/{unique_id}{extension}"
    
    def upload_image(
        self,
        base64_image: str,
        patient_id: str,
        consultation_id: Optional[str] = None
    ) -> Optional[dict]:
        """
        Upload base64 encoded image to Digital Ocean Spaces
        
        Args:
            base64_image: Base64 encoded image string
            patient_id: Patient identifier
            consultation_id: Optional consultation/trace ID for linking
            
        Returns:
            Dict with upload details or None if failed:
            {
                "url": "https://...",
                "key": "images/...",
                "size": 12345,
                "content_type": "image/jpeg"
            }
        """
        if not self.client:
            print("⚠️  Spaces client not initialized - skipping image upload")
            return None
        
        try:
            # Decode base64 image
            image_bytes, content_type = self._decode_base64_image(base64_image)
            
            # Generate object key
            object_key = self._generate_object_key(patient_id, content_type)
            
            # Prepare metadata
            metadata = {
                'patient-id': patient_id,
                'uploaded-at': datetime.utcnow().isoformat()
            }
            if consultation_id:
                metadata['consultation-id'] = consultation_id
            
            # Upload to Spaces
            self.client.put_object(
                Bucket=self.spaces_bucket,
                Key=object_key,
                Body=image_bytes,
                ContentType=content_type,
                ACL='private',  # Keep images private
                Metadata=metadata
            )
            
            # Generate public URL (if bucket has CDN enabled)
            # Format: https://{bucket}.{region}.cdn.digitaloceanspaces.com/{key}
            cdn_url = f"https://{self.spaces_bucket}.{self.spaces_region}.cdn.digitaloceanspaces.com/{object_key}"
            
            # For private access, generate signed URL (valid for 1 hour)
            signed_url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.spaces_bucket,
                    'Key': object_key
                },
                ExpiresIn=3600  # 1 hour
            )
            
            result = {
                "url": signed_url,  # Use signed URL for private access
                "cdn_url": cdn_url,  # CDN URL (only works if ACL is public)
                "key": object_key,
                "size": len(image_bytes),
                "content_type": content_type,
                "bucket": self.spaces_bucket,
                "region": self.spaces_region
            }
            
            print(f"📤 Uploaded image to Spaces: {object_key} ({len(image_bytes)} bytes)")
            
            return result
            
        except ClientError as e:
            print(f"❌ Failed to upload image to Spaces: {e.response['Error']['Message']}")
            return None
        except Exception as e:
            print(f"❌ Failed to upload image: {str(e)}")
            return None
    
    def get_signed_url(self, object_key: str, expires_in: int = 3600) -> Optional[str]:
        """
        Generate signed URL for private image access
        
        Args:
            object_key: Object key in Spaces
            expires_in: URL expiration time in seconds (default 1 hour)
            
        Returns:
            Signed URL or None
        """
        if not self.client:
            return None
        
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.spaces_bucket,
                    'Key': object_key
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            print(f"❌ Failed to generate signed URL: {str(e)}")
            return None
    
    def delete_image(self, object_key: str) -> bool:
        """
        Delete image from Spaces
        
        Args:
            object_key: Object key to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
        
        try:
            self.client.delete_object(
                Bucket=self.spaces_bucket,
                Key=object_key
            )
            print(f"🗑️  Deleted image from Spaces: {object_key}")
            return True
        except ClientError as e:
            print(f"❌ Failed to delete image: {str(e)}")
            return False


# Global instance
_spaces_storage: Optional[SpacesStorage] = None


def get_spaces_storage() -> SpacesStorage:
    """Get or create SpacesStorage singleton instance"""
    global _spaces_storage
    if _spaces_storage is None:
        _spaces_storage = SpacesStorage()
    return _spaces_storage
