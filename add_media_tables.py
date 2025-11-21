#!/usr/bin/env python3
"""
Database migration script to add media management tables
"""
import asyncio
import asyncpg
from urllib.parse import quote_plus

async def add_media_tables():
    """Add media management tables to the database"""
    
    # Hardcoded database connection details with URL encoded password
    password = quote_plus("Dev#31padia")
    DATABASE_URL = f"postgresql://postgres:{password}@localhost:5432/postgres"
    
    print("Connecting to database: localhost:5432/postgres")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected to database successfully")
        
        # Check if media_files table exists
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'media_files')"
        )
        
        if table_exists:
            print("✅ media_files table already exists")
            
            # Check if old columns exist and remove them
            old_columns = ['user_id', 'original_filename', 'file_path', 'thumbnail_path', 'is_processed', 'is_public']
            for column in old_columns:
                column_exists = await conn.fetchval(
                    f"SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'media_files' AND column_name = '{column}')"
                )
                if column_exists:
                    print(f"🔄 Removing old column '{column}' from media_files table...")
                    await conn.execute(f"ALTER TABLE media_files DROP COLUMN {column}")
                    print(f"✅ Removed {column} column")
            
            # Check if duration column is float and change to integer
            duration_type = await conn.fetchval(
                "SELECT data_type FROM information_schema.columns WHERE table_name = 'media_files' AND column_name = 'duration'"
            )
            if duration_type == 'double precision':
                print("🔄 Changing duration column from float to integer...")
                await conn.execute("ALTER TABLE media_files ALTER COLUMN duration TYPE INTEGER USING duration::INTEGER")
                print("✅ Changed duration column type")
            
            # Check if file_data column exists
            column_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'media_files' AND column_name = 'file_data')"
            )
            
            if not column_exists:
                print("🔄 Adding file_data column to media_files table...")
                await conn.execute("""
                    ALTER TABLE media_files 
                    ADD COLUMN file_data TEXT,
                    ADD COLUMN thumbnail_data TEXT,
                    ADD COLUMN thumbnail_size INTEGER
                """)
                print("✅ Added file_data, thumbnail_data, and thumbnail_size columns")
                
                # Update existing records to have empty file_data
                await conn.execute("""
                    UPDATE media_files 
                    SET file_data = '', 
                        thumbnail_data = NULL, 
                        thumbnail_size = NULL 
                    WHERE file_data IS NULL
                """)
                print("✅ Updated existing records with empty file_data")
            else:
                print("✅ file_data column already exists")
        else:
            print("❌ media_files table does not exist. Please run the original migration first.")
            return
        
        # Check if media_edits table exists
        edits_table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'media_edits')"
        )
        
        if edits_table_exists:
            print("✅ media_edits table already exists")
            
            # Check if original_file_data column exists
            edits_column_exists = await conn.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'media_edits' AND column_name = 'original_file_data')"
            )
            
            if not edits_column_exists:
                print("🔄 Adding file data columns to media_edits table...")
                await conn.execute("""
                    ALTER TABLE media_edits 
                    ADD COLUMN original_file_data TEXT,
                    ADD COLUMN edited_file_data TEXT
                """)
                print("✅ Added original_file_data and edited_file_data columns")
                
                # Update existing records
                await conn.execute("""
                    UPDATE media_edits 
                    SET original_file_data = '', 
                        edited_file_data = '' 
                    WHERE original_file_data IS NULL
                """)
                print("✅ Updated existing media_edits records")
            else:
                print("✅ media_edits file data columns already exist")
        else:
            print("❌ media_edits table does not exist. Please run the original migration first.")
            return
        
        print("✅ Database migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        raise
    finally:
        if 'conn' in locals():
            await conn.close()
            print("✅ Database connection closed")

if __name__ == "__main__":
    asyncio.run(add_media_tables()) 