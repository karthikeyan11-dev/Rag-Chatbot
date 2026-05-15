import asyncio
import os
import sys
from sqlalchemy import text

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.db.database import engine

async def migrate():
    print("--- DATABASE MIGRATION: ADDING INTELLIGENCE COLUMNS ---")
    async with engine.begin() as conn:
        # Check if columns exist and add if missing
        try:
            await conn.execute(text("ALTER TABLE document_metadata ADD COLUMN IF NOT EXISTS summary TEXT"))
            await conn.execute(text("ALTER TABLE document_metadata ADD COLUMN IF NOT EXISTS key_topics TEXT"))
            await conn.execute(text("ALTER TABLE document_metadata ADD COLUMN IF NOT EXISTS document_type VARCHAR"))
            print("✅ Migration successful: Columns added to document_metadata.")
        except Exception as e:
            print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
