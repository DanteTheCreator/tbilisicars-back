import os
from minio import Minio
from minio.error import S3Error
from typing import Optional, BinaryIO
import io
from PIL import Image
import uuid
import urllib3
import warnings

# Suppress InsecureRequestWarning globally for MinIO connections with self-signed certs
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

class MinIOClient:
    def __init__(self):
        self.endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
        self.access_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
        self.secret_key = os.getenv('MINIO_SECRET_KEY', 'MinioSecurePass2025')
        self.secure = os.getenv('MINIO_SECURE', 'false').lower() == 'true'
        
        # Public endpoint for URL generation (accessible from browser)
        self.public_endpoint = os.getenv('MINIO_PUBLIC_ENDPOINT', 'tbilisicars.live:9000')
        self.public_secure = os.getenv('MINIO_PUBLIC_SECURE', 'true').lower() == 'true'
        self.force_http_urls = os.getenv('MINIO_FORCE_HTTP', 'false').lower() == 'true'
        
        # Debug environment variables
        print(f"[DEBUG] MINIO_ENDPOINT: {self.endpoint}")
        print(f"[DEBUG] MINIO_PUBLIC_ENDPOINT: {self.public_endpoint}")
        print(f"[DEBUG] MINIO_PUBLIC_SECURE: {self.public_secure}")
        
        self.vehicle_photos_bucket = os.getenv('MINIO_VEHICLE_PHOTOS_BUCKET', 'vehicle-photos')
        self.vehicle_documents_bucket = os.getenv('MINIO_VEHICLE_DOCUMENTS_BUCKET', 'vehicle-documents')
        self.user_documents_bucket = os.getenv('MINIO_USER_DOCUMENTS_BUCKET', 'user-documents')
        
        # For HTTPS connections, disable SSL verification for internal Docker network
        # This is acceptable for internal services with self-signed certificates
        http_client = None
        if self.secure:
            http_client = urllib3.PoolManager(
                cert_reqs='CERT_NONE',
                assert_hostname=False
            )
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
            http_client=http_client
        )
        
        # Client for public URL generation - also with SSL verification disabled
        public_http_client = None
        if self.public_secure:
            public_http_client = urllib3.PoolManager(
                cert_reqs='CERT_NONE',
                assert_hostname=False
            )
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        self.public_client = Minio(
            self.public_endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.public_secure,
            http_client=public_http_client
        )
        
        self._ensure_buckets_exist()
    
    def _ensure_buckets_exist(self):
        """Ensure all required buckets exist"""
        buckets = [
            self.vehicle_photos_bucket,
            self.vehicle_documents_bucket,
            self.user_documents_bucket
        ]
        
        for bucket in buckets:
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    print(f"Created bucket: {bucket}")
            except S3Error as e:
                print(f"Error creating bucket {bucket}: {e}")
    
    def upload_vehicle_photo(self, file: BinaryIO, filename: str, vehicle_id: int) -> Optional[str]:
        """
        Upload a vehicle photo and return the object name
        """
        try:
            # Generate unique filename
            file_extension = filename.split('.')[-1].lower()
            object_name = f"vehicles/{vehicle_id}/{uuid.uuid4().hex}.{file_extension}"
            
            # Optimize image if it's an image file
            if file_extension in ['jpg', 'jpeg', 'png', 'webp']:
                optimized_file = self._optimize_image(file, file_extension)
                file_size = len(optimized_file.getvalue())
                optimized_file.seek(0)
                
                self.client.put_object(
                    self.vehicle_photos_bucket,
                    object_name,
                    optimized_file,
                    length=file_size,
                    content_type=f"image/{file_extension}"
                )
            else:
                # Upload as is for non-image files
                file.seek(0)
                self.client.put_object(
                    self.vehicle_photos_bucket,
                    object_name,
                    file,
                    length=-1,
                    part_size=10*1024*1024  # 10MB
                )
            
            return object_name
            
        except S3Error as e:
            print(f"Error uploading vehicle photo: {e}")
            return None
    
    def _optimize_image(self, file: BinaryIO, file_extension: str) -> io.BytesIO:
        """
        Optimize image by resizing and compressing
        """
        file.seek(0)
        image = Image.open(file)
        
        # Convert RGBA to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        
        # Resize if too large (max width 1200px)
        max_width = 1200
        if image.width > max_width:
            ratio = max_width / image.width
            new_height = int(image.height * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        # Save optimized image
        output = io.BytesIO()
        if file_extension.lower() in ['jpg', 'jpeg']:
            image.save(output, format='JPEG', quality=85, optimize=True)
        elif file_extension.lower() == 'png':
            image.save(output, format='PNG', optimize=True)
        elif file_extension.lower() == 'webp':
            image.save(output, format='WEBP', quality=85, optimize=True)
        else:
            image.save(output, format='JPEG', quality=85, optimize=True)
        
        return output
    
    def upload_document(self, file: BinaryIO, filename: str, document_type: str, entity_id: int) -> Optional[str]:
        """
        Upload a document (vehicle or user related)
        """
        try:
            file_extension = filename.split('.')[-1].lower()
            object_name = f"{document_type}/{entity_id}/{uuid.uuid4().hex}.{file_extension}"
            
            bucket = self.vehicle_documents_bucket if document_type.startswith('vehicle') else self.user_documents_bucket
            
            file.seek(0)
            self.client.put_object(
                bucket,
                object_name,
                file,
                length=-1,
                part_size=10*1024*1024  # 10MB
            )
            
            return object_name
            
        except S3Error as e:
            print(f"Error uploading document: {e}")
            return None
    
    def get_presigned_url(self, bucket: str, object_name: str, expires_in_hours: int = 24) -> Optional[str]:
        """
        Get a presigned URL for accessing an object (using public endpoint)
        """
        try:
            from datetime import timedelta
            print(f"[DEBUG] Generating presigned URL using public endpoint: {self.public_endpoint}")
            print(f"[DEBUG] Public secure: {self.public_secure}")
            
            # Generate presigned URL using the public client
            url = self.public_client.presigned_get_object(
                bucket,
                object_name,
                expires=timedelta(hours=expires_in_hours)
            )
            
            # If HTTPS fails, fallback to HTTP for presigned URLs
            if self.force_http_urls and url.startswith('https://'):
                print(f"[DEBUG] Converting HTTPS URL to HTTP due to MINIO_FORCE_HTTP=true")
                url = url.replace('https://', 'http://')
            
            print(f"[DEBUG] Generated URL: {url}")
            return url
        except S3Error as e:
            print(f"Error generating presigned URL: {e}")
            return None
    
    def get_vehicle_photo_url(self, object_name: str) -> Optional[str]:
        """
        Get URL for a vehicle photo
        """
        return self.get_presigned_url(self.vehicle_photos_bucket, object_name)
    
    def delete_object(self, bucket: str, object_name: str) -> bool:
        """
        Delete an object from a bucket
        """
        try:
            self.client.remove_object(bucket, object_name)
            return True
        except S3Error as e:
            print(f"Error deleting object: {e}")
            return False
    
    def delete_vehicle_photo(self, object_name: str) -> bool:
        """
        Delete a vehicle photo
        """
        return self.delete_object(self.vehicle_photos_bucket, object_name)
    
    def list_vehicle_photos(self, vehicle_id: int) -> list:
        """
        List all photos for a specific vehicle
        """
        try:
            objects = self.client.list_objects(
                self.vehicle_photos_bucket,
                prefix=f"vehicles/{vehicle_id}/",
                recursive=True
            )
            return [obj.object_name for obj in objects]
        except S3Error as e:
            print(f"Error listing vehicle photos: {e}")
            return []

# Global MinIO client instance
minio_client = MinIOClient()
