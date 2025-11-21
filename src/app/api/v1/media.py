from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import json
import base64
from ...core.db.database import async_get_db
from ...api.dependencies import get_current_user
from ...core.services.media_management import MediaManagementService
from ...models.media import MediaFile
from ...models.project import Project
from ...models.content import ContentGeneration
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from datetime import datetime

# Initialize templates
templates = Jinja2Templates(directory="templates")

router = APIRouter(prefix="/api/v1/media", tags=["media"])

@router.get("/library", response_class=HTMLResponse)
async def media_library_page(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """Media library page"""
    return templates.TemplateResponse("media_library.html", {
        "request": request,
        "user": current_user
    })

@router.get("/files/{media_file_id}/data")
async def serve_media_file_data(
    media_file_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """Serve media file data from database"""
    print(f"[DEBUG] === SERVING MEDIA FILE DATA ===")
    print(f"[DEBUG] Media file ID: {media_file_id}")
    print(f"[DEBUG] User ID: {current_user['id']}")
    
    media_service = MediaManagementService()
    
    try:
        media_file = await media_service.get_media_file(
            db=db,
            media_file_id=media_file_id,
            user_id=current_user["id"]
        )
        
        print(f"[DEBUG] Media file found: {media_file is not None}")
        if media_file:
            print(f"[DEBUG] Media file: ID={media_file.id}, Type={media_file.file_type}, MIME={media_file.mime_type}")
        
        if not media_file:
            print(f"[DEBUG] Media file not found")
            raise HTTPException(status_code=404, detail="Media file not found")
        
        # Decode base64 data
        file_data = base64.b64decode(media_file.file_data.encode('utf-8'))
        print(f"[DEBUG] Decoded file data size: {len(file_data)} bytes")
        
        return Response(
            content=file_data,
            media_type=media_file.mime_type,
            headers={
                "Content-Disposition": f"inline; filename={media_file.filename}",
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DEBUG] Error serving media file: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to serve media file: {str(e)}")

@router.get("/files/{media_file_id}/thumbnail")
async def serve_media_thumbnail(
    media_file_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """Serve media thumbnail from database"""
    media_service = MediaManagementService()
    
    try:
        media_file = await media_service.get_media_file(
            db=db,
            media_file_id=media_file_id,
            user_id=current_user["id"]
        )
        
        if not media_file:
            raise HTTPException(status_code=404, detail="Media file not found")
        
        if not media_file.thumbnail_data:
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        
        # Decode base64 thumbnail data
        thumbnail_data = base64.b64decode(media_file.thumbnail_data.encode('utf-8'))
        
        return Response(
            content=thumbnail_data,
            media_type="image/jpeg",
            headers={
                "Content-Disposition": f"inline; filename=thumb_{media_file.filename}",
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to serve thumbnail: {str(e)}")

@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    title: str = Form(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """Upload a media file (image or video)"""
    print(f"[DEBUG] === UPLOAD FUNCTION STARTED ===")
    print(f"[DEBUG] File object: {file}")
    print(f"[DEBUG] File filename: {file.filename if file else 'None'}")
    print(f"[DEBUG] File content type: {file.content_type if file else 'None'}")
    print(f"[DEBUG] Title: {title}")
    print(f"[DEBUG] Current user: {current_user}")
    
    # Validate file
    if not file or not file.filename:
        print(f"[DEBUG] No file provided")
        raise HTTPException(status_code=400, detail="No file provided")
    
    print(f"[DEBUG] Uploading file '{file.filename}' for user {current_user['id']}")
    print(f"[DEBUG] File content type: {file.content_type}")
    
    # Check file size (50MB limit)
    try:
        file_data = await file.read()
        print(f"[DEBUG] File size: {len(file_data)} bytes")
        if len(file_data) > 50 * 1024 * 1024:  # 50MB
            raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB")
    except Exception as e:
        print(f"[DEBUG] Error reading file: {e}")
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    # Reset file position for service
    await file.seek(0)
    
    # Check file type - be more flexible with content type detection
    allowed_image_types = ["image/jpeg", "image/png", "image/gif", "image/webp", "image/jpg"]
    allowed_video_types = ["video/mp4", "video/avi", "video/mov", "video/wmv", "video/flv", "video/webm"]
    
    content_type = file.content_type or ""
    print(f"[DEBUG] Content type: {content_type}")
    
    # Try to determine file type from content type first
    if content_type in allowed_image_types:
        file_type = "image"
        mime_type = content_type
    elif content_type in allowed_video_types:
        file_type = "video"
        mime_type = content_type
    else:
        # Fallback to mimetypes module
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file.filename)
        file_type = "image" if mime_type and mime_type.startswith("image/") else "video"
        print(f"[DEBUG] Fallback - MIME type: {mime_type}, file type: {file_type}")
    
    # Validate file type
    if file_type == "image" and mime_type not in allowed_image_types:
        raise HTTPException(status_code=400, detail=f"Unsupported image type: {mime_type}")
    elif file_type == "video" and mime_type not in allowed_video_types:
        raise HTTPException(status_code=400, detail=f"Unsupported video type: {mime_type}")
    
    print(f"[DEBUG] Final file type: {file_type}, MIME type: {mime_type}")
    
    # Simple test to see if we reach this point
    print(f"[DEBUG] Simple test - if you see this, we passed file validation")
    
    # Test database connection
    print(f"[DEBUG] Testing database connection...")
    try:
        # Test a simple database query
        result = await db.execute(select(1))
        print(f"[DEBUG] Database connection successful")
    except Exception as e:
        print(f"[DEBUG] Database connection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")
    
    print(f"[DEBUG] Database test completed, about to create service...")
    
    # Upload file
    try:
        print(f"[DEBUG] About to create MediaManagementService...")
        media_service = MediaManagementService()
        print(f"[DEBUG] MediaManagementService created successfully")
    except Exception as e:
        print(f"[DEBUG] Error creating MediaManagementService: {e}")
        print(f"[DEBUG] Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Service initialization failed: {str(e)}")
    
    try:
        print(f"[DEBUG] Processing upload for user {current_user['id']}")
        
        # Determine file type and mime type
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file.filename)
        file_type = "image" if mime_type and mime_type.startswith("image/") else "video"
        print(f"[DEBUG] File type: {file_type}, MIME type: {mime_type}")
        
        print(f"[DEBUG] About to call upload_media_file...")
        print(f"[DEBUG] Parameters: user_id={current_user['id']}, filename={file.filename}, title={title}")
        
        media_file = await media_service.upload_media_file(
            db=db,
            user_id=current_user["id"],
            file_data=file_data,
            original_filename=file.filename,
            title=title,
            description=None,
            tags=None
        )
        
        print(f"[DEBUG] File uploaded successfully with ID {media_file.id}")
        
        return JSONResponse({
            "status": "success",
            "message": "File uploaded successfully",
            "media_file": {
                "id": media_file.id,
                "filename": media_file.filename,
                "title": media_file.title,
                "file_type": media_file.file_type,
                "file_path": f"/api/v1/media/files/{media_file.id}/data",
                "thumbnail_path": f"/api/v1/media/files/{media_file.id}/thumbnail",
                "width": media_file.width,
                "height": media_file.height,
                "duration": media_file.duration,
                "file_size": media_file.file_size
            }
        })
        
    except Exception as e:
        print(f"[DEBUG] Error uploading file: {e}")
        print(f"[DEBUG] Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        
        # Return more specific error message
        if "400" in str(e) or "Bad Request" in str(e):
            raise HTTPException(status_code=400, detail=f"Upload validation failed: {str(e)}")
        elif "404" in str(e) or "Not Found" in str(e):
            raise HTTPException(status_code=404, detail=f"Upload failed - not found: {str(e)}")
        elif "500" in str(e) or "Internal Server Error" in str(e):
            raise HTTPException(status_code=500, detail=f"Upload failed - server error: {str(e)}")
        else:
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/files")
async def get_media_files(
    file_type: Optional[str] = Query(None, description="Filter by file type: image or video"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """Get user's media files"""
    print(f"[DEBUG] Getting media files for user {current_user['id']}")
    media_service = MediaManagementService()
    
    try:
        # First, ensure user has a library
        library = await media_service.get_user_library(db, current_user["id"])
        if not library:
            print(f"[DEBUG] Creating library for user {current_user['id']}")
            library = await media_service.create_user_library(db, current_user["id"])
        
        media_files = await media_service.get_user_media_files(
            db=db,
            user_id=current_user["id"],
            file_type=file_type,
            limit=limit,
            offset=offset
        )
        
        print(f"[DEBUG] Found {len(media_files)} media files")
        
        # Debug: Print each media file
        for mf in media_files:
            print(f"[DEBUG] Media file: ID={mf.id}, Title={mf.title}, Type={mf.file_type}")
        
        return JSONResponse({
            "status": "success",
            "media_files": [
                {
                    "id": mf.id,
                    "filename": mf.filename,
                    "title": mf.title,
                    "description": mf.description,
                    "file_type": mf.file_type,
                    "file_path": f"/api/v1/media/files/{mf.id}/data",
                    "thumbnail_path": f"/api/v1/media/files/{mf.id}/thumbnail",
                    "width": mf.width,
                    "height": mf.height,
                    "duration": mf.duration,
                    "file_size": mf.file_size,
                    "tags": mf.tags.get("tags", []) if mf.tags else [],
                    "created_at": mf.created_at.isoformat() if mf.created_at else None
                }
                for mf in media_files
            ]
        })
        
    except Exception as e:
        print(f"[DEBUG] Error getting media files: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get media files: {str(e)}")

@router.get("/files/{media_file_id}")
async def get_media_file(
    media_file_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """Get specific media file"""
    print(f"[DEBUG] Getting media file {media_file_id} for user {current_user['id']}")
    media_service = MediaManagementService()
    
    try:
        media_file = await media_service.get_media_file(
            db=db,
            media_file_id=media_file_id,
            user_id=current_user["id"]
        )
        
        print(f"[DEBUG] Media file found: {media_file is not None}")
        if media_file:
            print(f"[DEBUG] Media file ID: {media_file.id}, Title: {media_file.title}")
        
        if not media_file:
            print(f"[DEBUG] Media file not found")
            raise HTTPException(status_code=404, detail="Media file not found")
        
        return JSONResponse({
            "status": "success",
            "media_file": {
                "id": media_file.id,
                "filename": media_file.filename,
                "title": media_file.title,
                "description": media_file.description,
                "file_type": media_file.file_type,
                "file_path": f"/api/v1/media/files/{media_file.id}/data",
                "thumbnail_path": f"/api/v1/media/files/{media_file.id}/thumbnail",
                "width": media_file.width,
                "height": media_file.height,
                "duration": media_file.duration,
                "file_size": media_file.file_size,
                "tags": media_file.tags.get("tags", []) if media_file.tags else [],
                "created_at": media_file.created_at.isoformat() if media_file.created_at else None
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DEBUG] Error getting media file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get media file: {str(e)}")

@router.post("/files/{media_file_id}/edit")
async def edit_media_file(
    media_file_id: int,
    edit_type: str = Form(...),
    edit_params: str = Form(...),  # JSON string
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """Edit a media file"""
    
    # Parse edit parameters
    try:
        params = json.loads(edit_params)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid edit parameters")
    
    # Validate edit type
    allowed_edit_types = ["crop", "resize", "filter", "brightness", "contrast", "trim"]
    if edit_type not in allowed_edit_types:
        raise HTTPException(status_code=400, detail=f"Invalid edit type. Allowed: {allowed_edit_types}")
    
    media_service = MediaManagementService()
    
    try:
        edited_file = await media_service.edit_media_file(
            db=db,
            media_file_id=media_file_id,
            user_id=current_user["id"],
            edit_type=edit_type,
            edit_params=params
        )
        
        if not edited_file:
            raise HTTPException(status_code=404, detail="Media file not found or edit failed")
        
        return JSONResponse({
            "status": "success",
            "message": "File edited successfully",
            "media_file": {
                "id": edited_file.id,
                "updated_at": edited_file.updated_at.isoformat() if edited_file.updated_at else None
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Edit failed: {str(e)}")

@router.delete("/files/{media_file_id}")
async def delete_media_file(
    media_file_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """Delete a media file"""
    media_service = MediaManagementService()
    
    try:
        success = await media_service.delete_media_file(
            db=db,
            media_file_id=media_file_id,
            user_id=current_user["id"]
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Media file not found")
        
        return JSONResponse({
            "status": "success",
            "message": "Media file deleted successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

@router.post("/projects/{project_id}/use-media")
async def use_media_in_project(
    project_id: int,
    media_file_id: int = Form(...),
    platform: Optional[str] = Form(None),
    usage_type: str = Form("primary"),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db)
):
    """Use a media file in a project"""
    
    # Check project ownership
    project_result = await db.execute(
        select(Project).where(
            and_(
                Project.id == project_id,
                Project.created_by_user_id == current_user["id"]
            )
        )
    )
    project = project_result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check media file ownership
    media_service = MediaManagementService()
    media_file = await media_service.get_media_file(
        db=db,
        media_file_id=media_file_id,
        user_id=current_user["id"]
    )
    
    if not media_file:
        raise HTTPException(status_code=404, detail="Media file not found")
    
    # Create project media association
    from ...models.media import ProjectMedia
    project_media = ProjectMedia(
        project_id=project_id,
        media_file_id=media_file_id,
        platform=platform,
        usage_type=usage_type,
        created_at=datetime.utcnow()
    )
    
    db.add(project_media)
    await db.commit()
    
    return JSONResponse({
        "status": "success",
        "message": "Media file associated with project"
    }) 