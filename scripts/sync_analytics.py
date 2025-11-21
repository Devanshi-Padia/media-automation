#!/usr/bin/env python3
"""
Test script to manually sync analytics data for all projects.
"""

import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from app.core.services.analytics_sync import AnalyticsSyncService
from app.core.db.database import async_get_db

async def main():
    """Main function to sync analytics for all projects"""
    print("Starting analytics sync for all projects...")
    
    try:
        db_gen = async_get_db()
        async for db in db_gen:
            sync_service = AnalyticsSyncService()
            result = await sync_service.sync_all_projects_analytics(db)
            
            print("Analytics sync completed!")
            print(f"Total projects processed: {result.get('total_projects', 0)}")
            print("Results:")
            for project_id, project_result in result.get('results', {}).items():
                print(f"  Project {project_id}: {project_result}")
            break
                
    except Exception as e:
        print(f"Error during analytics sync: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())