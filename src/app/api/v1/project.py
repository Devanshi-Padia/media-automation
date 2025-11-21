from fastapi import APIRouter, Request, Depends, Form, UploadFile, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from ...core.db.database import async_get_db
from ...models import Project, SocialMediaCredential, ContentGeneration
from ...api.dependencies import get_current_user
from starlette.status import HTTP_303_SEE_OTHER
from fastapi.templating import Jinja2Templates
from ...templates import templates
from sqlalchemy import select, desc, func
import os
from ...core.services.social_media import SocialMediaService
from fastapi.responses import JSONResponse
import asyncio
from typing import List
from fastapi import HTTPException
from ...models.scheduled_post import ScheduledPost

router = APIRouter(tags=["projects"])

@router.get("/projects")
async def get_all_projects(
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(5, ge=1, le=100)
):
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Project)
        .where(Project.created_by_user_id == current_user["id"])
        .order_by(desc(Project.id))
        .offset(offset)
        .limit(per_page)
    )
    projects = result.scalars().all()
    total = await db.scalar(select(func.count()).select_from(Project).where(Project.created_by_user_id == current_user["id"]))
    def project_to_dict(p):
        return {
            "id": p.id,
            "name": p.name,
            "topic": p.topic,
            "status": p.status,
            "social_medias": p.social_medias,
        }
    
    from fastapi.responses import JSONResponse
    response = JSONResponse({"projects": [project_to_dict(p) for p in projects], "total": total})
    # Add headers to prevent caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@router.get("/projects/create", response_class=HTMLResponse)
async def create_project_form(request: Request, current_user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("create_project.html", {
        "request": request, 
        "user": current_user,
        "username": current_user.get('username')
    })

@router.post("/projects/create")
async def create_project(
    request: Request,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
    name: str = Form(...),
    topic: str = Form(...),
    with_image: str = Form(...),
    content_type: str = Form(...),
    social_medias: List[str] = Form(...),  # comma-separated
    # Credentials (all optional, will be filtered in frontend)
    twitter_api_key: str = Form(None),
    twitter_api_secret: str = Form(None),
    twitter_access_token: str = Form(None),
    twitter_access_secret: str = Form(None),
    
    fb_page_id: str = Form(None),
    fb_page_access_token: str = Form(None),
    ig_username: str = Form(None),
    ig_password: str = Form(None),
    
    linkedin_access_token: str = Form(None),
    linkedin_author_urn: str = Form(None),
    
    discord_webhook_url: str = Form(None),
    
    # Telegram credentials
    telegram_bot_token: str = Form(None),
    telegram_chat_id: str = Form(None),
):
    print(f"[DEBUG] current_user: {current_user}")
    from ...crud.crud_users import crud_users
    db_user = await crud_users.get(db=db, username=current_user.get("username"))
    if db_user:
        # db_user can be a model instance or a dict, handle both
        if isinstance(db_user, dict):
            user_id = db_user.get("id")
        else:
            user_id = getattr(db_user, "id", None)
    else:
        user_id = None
    print(f"[DEBUG] db_user: {db_user}, user_id: {user_id}")

    if user_id is None:
        print("[DEBUG] User not found. Cannot create project.")
        return HTMLResponse("User not found. Cannot create project.", status_code=404)

    try:
        project = Project(
            name=name,
            topic=topic,
            with_image=(with_image.lower() == "yes"),
            content_type=content_type,
            social_medias=",".join(social_medias),  
            created_by_user_id=current_user["id"],  
        )
        db.add(project)
        await db.flush()
        print(f"[DEBUG] Created project with ID: {project.id}")

        # Generate text and image
        from ...core.services.text_generation import TextGenerationService
        text_service = TextGenerationService()
        # Pass topic and content_type directly to the text generation service.
        # The service will construct the final prompt for the AI.
        generated_text_dict = text_service.generate_text(topic=topic, content_type=content_type)

        image_path = None
        if project.with_image:
            from ...core.services.image_generation import ImageGenerationService
            image_service = ImageGenerationService()
            image_path = await image_service.generate_image(prompt=project.topic, output_filename=f"project_{project.id}.png")
            project.image_path = image_path

        # Create a single ContentGeneration entry linked to the new project
        user_prompt = f"{topic} - {content_type}"
        content_generation = ContentGeneration(
            project_id=project.id,
            user_id=user_id,
            prompt=user_prompt,
            generated_text=generated_text_dict,
            image_path=image_path,
            include_news=True, # Assuming this is default behavior now
        )
        db.add(content_generation)
        await db.flush()
        print(f"[DEBUG] ContentGeneration entry created for project ID: {project.id}")
        
        # Save credentials for each selected platform
        platforms = [p.strip() for p in social_medias if p.strip()]
        for platform in platforms:
            # Skip saving if required credential for the platform is missing
            if platform == "X" and not twitter_api_key:
                continue
            if platform == "facebook" and not fb_page_id:
                continue
            if platform == "instagram" and not ig_username:
                continue
            if platform == "linkedin" and not linkedin_access_token:
                continue
            if platform == "discord" and not discord_webhook_url:
                continue
            if platform == "telegram" and not telegram_bot_token:
                continue
            print(f"[DEBUG] Saving credentials for platform: {platform}")
            print(f"[DEBUG] Credentials: twitter_api_key={twitter_api_key}, twitter_api_secret={twitter_api_secret}, twitter_access_token={twitter_access_token}, twitter_access_secret={twitter_access_secret}, fb_page_id={fb_page_id}, fb_page_access_token={fb_page_access_token}, ig_username={ig_username}, ig_password={ig_password}, linkedin_access_token={linkedin_access_token}, linkedin_author_urn={linkedin_author_urn}, discord_webhook_url={discord_webhook_url}, telegram_bot_token={telegram_bot_token}")
            
            # Convert platform name to lowercase for consistency
            platform_lower = platform.lower()
            if platform_lower == "x":
                platform_lower = "twitter"  # Map X to twitter for the service
            
            cred = SocialMediaCredential(
                project_id=project.id,
                platform=platform_lower,  # Save as lowercase
                twitter_api_key=twitter_api_key if platform == "X" else None,
                twitter_api_secret=twitter_api_secret if platform == "X" else None,
                twitter_access_token=twitter_access_token if platform == "X" else None,
                twitter_access_secret=twitter_access_secret if platform == "X" else None,
                fb_page_id=fb_page_id if platform == "facebook" else None,
                fb_page_access_token=fb_page_access_token if platform == "facebook" else None,
                ig_username=ig_username if platform == "instagram" else None,
                ig_password=ig_password if platform == "instagram" else None,
                linkedin_access_token=linkedin_access_token if platform == "linkedin" else None,
                linkedin_author_urn=linkedin_author_urn if platform == "linkedin" else None,
                discord_webhook_url=discord_webhook_url if platform == "discord" else None,
                telegram_bot_token=telegram_bot_token if platform == "telegram" else None,
                telegram_chat_id=telegram_chat_id if platform == "telegram" else None,
            )  # type: ignore
            db.add(cred)
        await db.commit()
        # Print all credentials saved for this project
        creds = await db.execute(select(SocialMediaCredential).where(SocialMediaCredential.project_id == project.id))
        creds = creds.scalars().all()
        print(f"[DEBUG] All SocialMediaCredential entries for project {project.id}:")
        for c in creds:
            print(f"  Platform: {c.platform}, twitter_api_key: {c.twitter_api_key}, fb_page_id: {c.fb_page_id}, ig_username: {c.ig_username}, linkedin_access_token: {c.linkedin_access_token}, discord_webhook_url: {c.discord_webhook_url}")

        return RedirectResponse(url=f"/api/v1/projects/{project.id}/review", status_code=HTTP_303_SEE_OTHER)
    except Exception as e:
        print(f"[DEBUG] Exception during project creation: {e}")
        return HTMLResponse(f"Error during project creation: {e}", status_code=500)

@router.get("/projects/search")
async def search_projects(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(
        select(Project)
        .where(Project.created_by_user_id == current_user["id"])
        .where(Project.name.ilike(f"%{q}%"))
    )
    projects = result.scalars().all()
    def project_to_dict(p):
        return {
            "id": p.id,
            "name": p.name,
            "topic": p.topic,
            "status": p.status,
            "social_medias": p.social_medias,
        }
    
    from fastapi.responses import JSONResponse
    response = JSONResponse({"projects": [project_to_dict(p) for p in projects]})
    # Add headers to prevent caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@router.get("/projects/history")
async def get_project_history(
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    per_page: int = Query(5, ge=1, le=100)
):
    offset = (page - 1) * per_page
    # Show all projects for the user, regardless of status
    result = await db.execute(
        select(Project)
        .where(Project.created_by_user_id == current_user["id"])
        .order_by(desc(Project.id))
        .offset(offset)
        .limit(per_page)
    )
    projects = result.scalars().all()
    total = await db.scalar(
        select(func.count()).select_from(Project).where(
            Project.created_by_user_id == current_user["id"]
        )
    )
    def project_to_dict(p):
        return {
            "id": p.id,
            "name": p.name,
            "topic": p.topic,
            "status": p.status,
            "social_medias": p.social_medias,
        }
    
    from fastapi.responses import JSONResponse
    response = JSONResponse({"projects": [project_to_dict(p) for p in projects], "total": total})
    # Add headers to prevent caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@router.get("/projects/{project_id}/review", response_class=HTMLResponse)
async def review_project(request: Request, project_id: int, db: AsyncSession = Depends(async_get_db), current_user: dict = Depends(get_current_user)):
    print(f"[DEBUG] review_project ENTRY: project_id={project_id}, current_user={current_user}")
    project = await db.get(Project, project_id)
    print(f"[DEBUG] review_project: fetched project id={getattr(project, 'id', None)}, created_by_user_id={getattr(project, 'created_by_user_id', None)}")
    # Temporarily allow any authenticated user to view any project for testing
    if not project:
        return HTMLResponse("Project not found", status_code=404)
    if not project or getattr(project, 'created_by_user_id', None) != current_user.get("id"):
        return HTMLResponse("Project not found or access denied", status_code=404)
    # Fetch credentials for social media preview
    from ...models import SocialMediaCredential
    credentials = await db.execute(
        select(SocialMediaCredential).where(SocialMediaCredential.project_id == project_id)
    )
    credentials = credentials.scalars().all()
    # Fetch ContentGeneration for this project
    from ...models.content import ContentGeneration
    content_generation = await db.scalar(
        select(ContentGeneration).where(ContentGeneration.project_id == project_id)
    )
    generated_text = None
    image_path = None
    if content_generation:
        generated_text = content_generation.generated_text
        image_path = content_generation.image_path
        if image_path and not image_path.startswith("/public/"):
            if image_path.startswith("public/"):
                image_path = "/" + image_path
            else:
                import os
                image_path = "/public/generated_images/" + os.path.basename(image_path)
    else:
        # Always provide a dict for the template
        generated_text = {
            "twitter": project.topic,
            "x": project.topic,
            "facebook": project.topic,
            "instagram": project.topic,
            "linkedin": project.topic,
            "discord": project.topic,
        }
        image_path = project.image_path
        if image_path and not image_path.startswith("/public/"):
            if image_path.startswith("public/"):
                image_path = "/" + image_path
            else:
                import os
                image_path = "/public/generated_images/" + os.path.basename(image_path)
    return templates.TemplateResponse(
        "review_project.html",
        {
            "request": request,
            "project": project,
            "credentials": credentials,
            "user": current_user,
            "username": current_user.get('username'),
            "generated_text": generated_text,
            "image_path": image_path
        }
    )

@router.get("/projects/{project_id}/schedule-details", response_class=HTMLResponse)
async def schedule_details_page(request: Request, project_id: int, current_user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("schedule_details.html", {
        "request": request, 
        "project_id": project_id,
        "username": current_user.get('username')
    })

@router.post("/projects/{project_id}/edit-image")
async def edit_project_image(request: Request, project_id: int, new_image: UploadFile = Form(None), db: AsyncSession = Depends(async_get_db), current_user: dict = Depends(get_current_user)):
    from ...models import Project
    project = await db.get(Project, project_id)
    if not project:
        return HTMLResponse("Project not found or access denied", status_code=404)
    # If no file is uploaded, generate a new image
    if new_image is None:
        from ...core.services.image_generation import ImageGenerationService
        image_service = ImageGenerationService()
        image_path = await image_service.generate_image(prompt=project.topic, output_filename=f"project_{project_id}.png")
        # Ensure the returned path is web-accessible
        if not image_path.startswith("/public/"):
            # If image_path is like 'public/generated_images/xxx.jpg', add leading slash
            if image_path.startswith("public/"):
                image_path = "/" + image_path
            else:
                image_path = "/public/generated_images/" + os.path.basename(image_path)
        project.image_path = image_path
        db.add(project)
        await db.commit()
        # Return JSON for AJAX
        return {"image_path": image_path}
    # If a file is uploaded, keep the old logic
    image_path = f"/public/generated_images/project_{project_id}.png"
    with open(image_path.lstrip("/"), "wb") as f:
        f.write(await new_image.read())
    project.image_path = image_path
    db.add(project)
    await db.commit()
    import time
    return RedirectResponse(url=f"/projects/{project_id}/review?image_preview_cache={int(time.time())}", status_code=HTTP_303_SEE_OTHER)

@router.post("/projects/{project_id}/edit-text")
async def edit_project_text(request: Request, project_id: int, new_text: str = Form(...), db: AsyncSession = Depends(async_get_db), current_user: dict = Depends(get_current_user)):
    from ...models import Project, ContentGeneration
    from sqlalchemy import select
    
    # Check if project exists and user has access
    result = await db.execute(
        Project.__table__.select().where(Project.id == project_id, Project.created_by_user_id == current_user["id"])
    )
    project_row = result.fetchone()
    if not project_row:
        return HTMLResponse("Project not found or access denied", status_code=404)
    
    # Get the project
    project = await db.get(Project, project_id)
    if not project:
        return HTMLResponse("Project not found or access denied", status_code=404)
    
    try:
        # Find existing content generation or create new one
        content_generation = await db.scalar(
            select(ContentGeneration).where(ContentGeneration.project_id == project_id)
        )
        
        if content_generation:
            # Update existing content generation
            content_generation.generated_text = new_text
            db.add(content_generation)
        else:
            # Create new content generation
            content_generation = ContentGeneration(
                project_id=project_id,
                generated_text=new_text,
                image_path=None  # Keep existing image if any
            )
            db.add(content_generation)
        
        await db.commit()
        await db.refresh(content_generation)
        
        # Check for AJAX request
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse({"status": "success", "message": "Text updated successfully"})
        
        return RedirectResponse(url=f"/api/v1/projects/{project_id}/review", status_code=HTTP_303_SEE_OTHER)
        
    except Exception as e:
        await db.rollback()
        print(f"[ERROR] Failed to update project text: {e}")
        
        # Check for AJAX request
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JSONResponse({"status": "error", "message": f"Error saving edits: {str(e)}"}, status_code=500)
        
        return HTMLResponse(f"Error saving edits: {str(e)}", status_code=500)

@router.post("/projects/{project_id}/post-now")
async def post_now_project(project_id: int, db: AsyncSession = Depends(async_get_db), current_user: dict = Depends(get_current_user)):
    # Fetch the project
    project = await db.get(Project, project_id)
    if not project or getattr(project, 'created_by_user_id', None) != current_user.get("id"):
        raise HTTPException(status_code=404, detail="Project not found or access denied")

    # This is where the service call was incorrect.
    # The method is post_to_social_media, and it needs the text, image path, and credentials.
    
    # Fetch credentials
    creds_result = await db.execute(select(SocialMediaCredential).where(SocialMediaCredential.project_id == project_id))
    all_creds = creds_result.scalars().all()
    
    # Create credentials map with proper platform name mapping
    credentials_map = {}
    for c in all_creds:
        platform = c.platform
        # Map platform names to match what the service expects
        if platform == "twitter":
            credentials_map["twitter"] = c.__dict__
            credentials_map["x"] = c.__dict__  # Also support "x" for Twitter
        else:
            credentials_map[platform] = c.__dict__
    
    # Filter by platforms selected in the project
    project_platforms = [p.strip().lower() for p in project.social_medias.split(',')]
    filtered_credentials = {}
    for platform, creds in credentials_map.items():
        if platform in project_platforms or (platform == "twitter" and "x" in project_platforms):
            filtered_credentials[platform] = creds
    credentials_map = filtered_credentials
    
    # Debug logging
    # print(f"[DEBUG] Project social_medias: {project.social_medias}")
    # print(f"[DEBUG] Found credentials: {len(all_creds)}")
    # print(f"[DEBUG] Credentials map: {credentials_map}")
    
    # Fetch content
    content_generation = await db.scalar(select(ContentGeneration).where(ContentGeneration.project_id == project_id))
    text_payload = content_generation.generated_text if content_generation else {"default": project.topic}
    
    image_path = None
    if project.with_image:
        image_path = content_generation.image_path if content_generation and content_generation.image_path else None
    
    # print(f"[DEBUG] Text payload: {text_payload}")
    # print(f"[DEBUG] Image path: {image_path}")

    service = SocialMediaService()
    results = service.post_to_social_media(text_payload, image_path, credentials_map)

    # Determine overall status and update project
    successful_platforms = results.get('successful_platforms', [])
    failed_platforms = results.get('failed_platforms', [])
    if successful_platforms and failed_platforms:
        project.status = "Partial"
    elif successful_platforms:
        project.status = "Posted"
    else:
        project.status = "Failed"

    # Save project status
    db.add(project)
    await db.commit()
    await db.refresh(project)

    # Return the detailed results from the service
    if successful_platforms and not failed_platforms:
        return {"status": "success", "message": results.get("message"), "details": results}
    elif successful_platforms and failed_platforms:
        return {"status": "partial", "message": results.get("message"), "details": results}
    else:
        # Provide more detailed error information
        error_message = results.get("error", "An unknown error occurred during posting.")
        failed_details = results.get("failed_platforms", [])
        if failed_details:
            error_message = f"Failed to post to: {', '.join(failed_details)}. Please check your credentials."
        
        raise HTTPException(status_code=500, detail=error_message)

@router.delete("/projects/{project_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user)
):
    project = await db.get(Project, project_id)
    if not project:
        return HTMLResponse("Project not found", status_code=404)
    
    # Optionally, restrict deletion to the creator:
    # if project.created_by_user_id != current_user.get("id"):
    #     return HTMLResponse("Not authorized to delete this project", status_code=403)
    
    # Delete the project
    await db.delete(project)
    await db.commit()
    
    # Verify deletion
    deleted_project = await db.get(Project, project_id)
    if deleted_project:
        # If project still exists, something went wrong
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete project")
    
    return

@router.post("/projects/fix-status")
async def fix_project_statuses(
    db: AsyncSession = Depends(async_get_db),
    current_user: dict = Depends(get_current_user)
):
    """Fix project statuses for completed scheduled posts"""
    from ...models.scheduled_post import ScheduledPost
    
    # Check for completed scheduled posts that haven't updated project status
    completed_posts = await db.execute(
        select(ScheduledPost).where(
            ScheduledPost.status == "completed",
            ScheduledPost.project_id.isnot(None)
        )
    )
    completed_posts = completed_posts.scalars().all()
    
    updated_count = 0
    for post in completed_posts:
        project = await db.get(Project, post.project_id)
        if project and project.status == "Pending":
            project.status = "Posted"
            db.add(project)
            updated_count += 1
    
    await db.commit()
    
    return {
        "status": "success",
        "message": f"Updated {updated_count} projects from 'Pending' to 'Posted'",
        "updated_count": updated_count
    }
