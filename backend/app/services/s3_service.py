import os
import boto3
import logging
from botocore.exceptions import ClientError
from io import BytesIO

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )
        self.bucket_name = os.getenv('AWS_S3_BUCKET_NAME')
        self.prefix = "company-documents"

    def upload_file(self, file_obj, filename: str, document_id: str = "default") -> bool:
        """Upload a file-like object to S3."""
        key = f"{self.prefix}/{document_id}/{filename}"
        try:
            self.s3_client.upload_fileobj(file_obj, self.bucket_name, key)
            logger.info(f"S3: Successfully uploaded {filename} to {key}")
            return True
        except ClientError as e:
            logger.error(f"S3 Upload Error: {e}")
            return False

    def list_files(self) -> list[str]:
        """List all filenames in the S3 bucket under the prefix."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.prefix
            )
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Extract filename from key: company-documents/doc_id/filename.pdf
                    key = obj['Key']
                    parts = key.split('/')
                    if len(parts) >= 3:
                        files.append(parts[-1])
            return list(set(files)) # Ensure uniqueness
        except ClientError as e:
            logger.error(f"S3 List Error: {e}")
            return []

    def get_file_content(self, filename: str) -> BytesIO:
        """Retrieve file content from S3 as a BytesIO stream."""
        # Note: In a production multi-document_id setup, we'd need the full key.
        # For this implementation, we search for the key by filename.
        try:
            # Search for the key
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.prefix
            )
            target_key = None
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith(f"/{filename}"):
                        target_key = obj['Key']
                        break
            
            if not target_key:
                logger.error(f"S3: File {filename} not found in bucket.")
                return None

            file_obj = BytesIO()
            self.s3_client.download_fileobj(self.bucket_name, target_key, file_obj)
            file_obj.seek(0)
            return file_obj
        except ClientError as e:
            logger.error(f"S3 Download Error: {e}")
            return None

    def delete_file(self, filename: str) -> bool:
        """Delete a file from S3."""
        try:
            # Find the key first
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=self.prefix
            )
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith(f"/{filename}"):
                        self.s3_client.delete_object(Bucket=self.bucket_name, Key=obj['Key'])
                        logger.info(f"S3: Successfully deleted {obj['Key']}")
                        return True
            return False
        except ClientError as e:
            logger.error(f"S3 Delete Error: {e}")
            return False

# Singleton instance
s3_service = S3Service()
