import os
import asyncio
import logging
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

# Hardened for Windows Async Compatibility
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("CloudDiagnostic")

# Load environment
load_dotenv()

async def test_rds():
    """Test RDS PostgreSQL Connectivity."""
    logger.info("--- Testing AWS RDS Connectivity ---")
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        logger.error("DATABASE_URL not found in .env")
        return False
        
    if "rds-endpoint" in db_url:
        logger.warning(f"CRITICAL: Placeholder RDS endpoint detected: {db_url.split('@')[-1]}")
    
    try:
        # We set a short timeout for the diagnostic
        engine = create_async_engine(db_url, connect_args={"connect_timeout": 5})
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            version = result.scalar()
            logger.info(f"SUCCESS: Connected to RDS. Version: {version}")
        await engine.dispose()
        return True
    except Exception as e:
        logger.error(f"FAILURE: RDS Connectivity failed. Error: {e}")
        return False

def test_s3():
    """Test AWS S3 Connectivity and Permissions."""
    logger.info("--- Testing AWS S3 Connectivity ---")
    bucket = os.getenv("AWS_S3_BUCKET_NAME")
    ak = os.getenv("AWS_ACCESS_KEY_ID")
    sk = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    if not all([bucket, ak, sk]) or "your_access_key" in str(ak):
        logger.error("FAILURE: S3 credentials are missing or are PLACEHOLDERS in .env")
        return False

    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=ak,
            aws_secret_access_key=sk,
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )
        s3.list_objects_v2(Bucket=bucket, MaxKeys=1)
        logger.info(f"SUCCESS: S3 bucket '{bucket}' is reachable and accessible.")
        return True
    except Exception as e:
        logger.error(f"FAILURE: S3 Connectivity failed. Error: {e}")
        return False

async def main():
    logger.info("Starting Cloud Infrastructure Audit...")
    
    rds_status = await test_rds()
    print("\n")
    s3_status = test_s3()
    
    print("\n" + "="*50)
    print("           FINAL CLOUD READINESS REPORT           ")
    print("="*50)
    print(f" AWS RDS PostgreSQL: {'[ READY ]' if rds_status else '[ PLACEHOLDER/FAILED ]'}")
    print(f" AWS S3 Storage:    {'[ READY ]' if s3_status else '[ PLACEHOLDER/FAILED ]'}")
    print("-" * 50)
    if not rds_status or not s3_status:
        print(" ACTION REQUIRED: Please update the .env file with your ")
        print(" real AWS Access Keys and RDS Endpoint to activate the ")
        print(" production-grade cloud-native storage.")
    else:
        print(" SYSTEM STATUS: ALL CLOUD SERVICES OPERATIONAL")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
