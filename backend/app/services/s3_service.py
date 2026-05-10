import os
import boto3
import logging
from botocore.exceptions import ClientError
from io import BytesIO

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        # HARDENING: Force load .env from the backend root if not already loaded
        env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
        if not os.getenv('AWS_S3_BUCKET_NAME'):
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=env_path)
            
        self.bucket_name = os.getenv('AWS_S3_BUCKET_NAME')
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )
        # USER-SCOPED STORAGE ROOT
        self.prefix = "users"

    def upload_file(self, file_obj, filename: str, user_id: int, document_id: str) -> str:
        """
        Upload a file-like object to a user-scoped S3 path.
        Structure: users/{user_id}/documents/{document_id}/{filename}
        Returns the full S3 key if successful, else None.
        """
        key = f"{self.prefix}/{user_id}/documents/{document_id}/{filename}"
        try:
            self.s3_client.upload_fileobj(file_obj, self.bucket_name, key)
            logger.info(f"S3: Successfully uploaded {filename} to {key}")
            return key
        except ClientError as e:
            logger.error(f"S3 Upload Error: {e}")
            return None

    def delete_object(self, key: str) -> bool:
        """Delete an object from S3 by its full key."""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"S3: Successfully deleted {key}")
            return True
        except ClientError as e:
            logger.error(f"S3 Delete Error: {e}")
            return False

    def list_user_files(self, user_id: int) -> list[dict]:
        """List all files belonging to a specific user."""
        user_prefix = f"{self.prefix}/{user_id}/documents/"
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=user_prefix
            )
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # users/{user_id}/documents/{document_id}/{filename}
                    key = obj['Key']
                    parts = key.split('/')
                    if len(parts) >= 5:
                        files.append({
                            "key": key,
                            "filename": parts[-1],
                            "document_id": parts[-2],
                            "size": obj['Size'],
                            "last_modified": obj['LastModified']
                        })
            return files
        except ClientError as e:
            logger.error(f"S3 List Error: {e}")
            return []

    def get_file_content(self, key: str) -> BytesIO:
        """Retrieve file content from S3 as a BytesIO stream using the full key."""
        try:
            file_obj = BytesIO()
            self.s3_client.download_fileobj(self.bucket_name, key, file_obj)
            file_obj.seek(0)
            return file_obj
        except ClientError as e:
            logger.error(f"S3 Download Error: {e}")
            return None

    def delete_legacy_file(self, filename: str) -> bool:
        """TEMPORARY: Delete a file from the legacy 'company-documents' prefix."""
        legacy_prefix = "company-documents"
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=legacy_prefix
            )
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith(f"/{filename}"):
                        self.s3_client.delete_object(Bucket=self.bucket_name, Key=obj['Key'])
                        logger.info(f"S3: Successfully deleted legacy file {obj['Key']}")
                        return True
            return False
        except ClientError as e:
            logger.error(f"S3 Legacy Delete Error: {e}")
            return False

# Singleton instance
s3_service = S3Service()
