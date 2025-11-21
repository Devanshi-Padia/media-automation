import os
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import token
import requests
from datetime import datetime

# Configure logging to suppress debug messages
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("tzlocal").setLevel(logging.WARNING)
logging.getLogger("aiosqlite").setLevel(logging.WARNING)

from fastapi import FastAPI, Request, Depends, Form, HTTPException, status, Query
from fastapi.responses import RedirectResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi import APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastcrud.paginated import response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from .core.db.database import async_get_db
from sqlalchemy import select

from .admin.initialize import create_admin_interface
from .api import router
from .core.config import settings
from .core.setup import create_application, lifespan_factory
from .api.v1.posts import router as posts_router
from .api.v1 import router as api_v1_router
from .templates import templates
from .api.dependencies import get_current_user, get_optional_user
from .core.scheduler import schedule_apscheduler_job
from .api.v1 import project, scheduled_tasks, users
from .api.v1 import media
from .api.v1 import notifications
from .models import User, Project, ScheduledPost

admin = create_admin_interface()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
static_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'static')
static_dir = os.path.abspath(static_dir)
templates_dir = os.path.join(BASE_DIR, "templates")

# Security
security = HTTPBearer()

@asynccontextmanager
async def lifespan_with_admin(app: FastAPI) -> AsyncGenerator[None, None]:
    """Custom lifespan that includes admin initialization and starts APScheduler."""
    # Get the default lifespan
    default_lifespan = lifespan_factory(settings)

    # Run the default lifespan initialization and our admin initialization
    async with default_lifespan(app):
        # Initialize admin interface if it exists
        if admin:
            # Initialize admin database and setup
            await admin.initialize()
        # Start APScheduler
        # print("[APScheduler] Starting scheduler in lifespan event")
        schedule_apscheduler_job(app)
        yield


app = create_application(router=router, settings=settings, lifespan=lifespan_with_admin)

# Mount admin interface if enabled
if admin:
    app.mount(settings.CRUD_ADMIN_MOUNT_PATH, admin.app)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount the 'public' directory to serve generated images and other static assets
app.mount("/public", StaticFiles(directory="public"), name="public")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins since we're consolidating
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function to get auth headers
def get_headers(token: str):
    return {"Authorization": f"Bearer {token}"} if token else {}

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/landing")

@app.get("/landing", response_class=HTMLResponse, include_in_schema=False, name="landing")
async def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/login", response_class=HTMLResponse, include_in_schema=False, name="login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_post(request: Request, username: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(async_get_db)):
    print(f"[DEBUG] Login attempt for username: {username}")
    from .core.security import authenticate_user, create_access_token
    from datetime import timedelta
    from .core.config import settings
    
    try:
        # Authenticate user
        user = await authenticate_user(username_or_email=username, password=password, db=db)
        if not user:
            return templates.TemplateResponse("login.html", {
                "request": request, 
                "error": "Invalid username or password."
            })
        
        print(f"[DEBUG] Login successful for user: {user.get('username')}")
        print(f"[DEBUG] User is_superuser: {user.get('is_superuser')}")
        print(f"[DEBUG] User ID: {user.get('id')}")
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = await create_access_token(
            data={"sub": user["username"]}, 
            expires_delta=access_token_expires
        )
        
        # Create redirect response with cookie
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie('access_token', access_token, httponly=True, samesite='Lax')
        return response
        
    except Exception as e:
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": f"Login failed: {str(e)}"
        })

@app.get("/register", response_class=HTMLResponse, include_in_schema=False, name="register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})

@app.post("/register", response_class=HTMLResponse, include_in_schema=False)
async def register_post(
    request: Request, 
    name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...)
):
    API_URL = "http://127.0.0.1:8000/api/v1"
    
    if not (name and username and email and password and confirm_password):
        return templates.TemplateResponse("register.html", {
            "request": request, 
            "error": "All fields are required."
        })
    elif password != confirm_password:
        return templates.TemplateResponse("register.html", {
            "request": request, 
            "error": "Passwords do not match."
        })
    elif len(password) < 8:
        return templates.TemplateResponse("register.html", {
            "request": request, 
            "error": "Password must be at least 8 characters."
        })
    
    payload = {
        "name": name,
        "username": username,
        "email": email,
        "password": password
    }
    
    resp = requests.post(f"{API_URL}/user", json=payload)
    if resp.status_code == 201:
        return RedirectResponse(url="/login", status_code=302)
    else:
        try:
            err = resp.json()
            error = f"Registration failed: {err.get('detail', resp.text)}"
        except Exception:
            error = f"Registration failed: {resp.text}"
        
        return templates.TemplateResponse("register.html", {
            "request": request, 
            "error": error
        })

@app.get("/logout", include_in_schema=False)
async def logout():
    response = RedirectResponse(url="/landing", status_code=302)
    response.set_cookie('access_token', '', expires=0)
    return response

@app.get("/user_panel", response_class=HTMLResponse, include_in_schema=False, name="user_panel")
async def user_panel(request: Request, current_user=Depends(get_current_user)):
    return templates.TemplateResponse("user_panel.html", {
        "request": request, 
        "username": current_user.get("username")
    })

@app.get("/check_admin_privileges", response_class=HTMLResponse)
async def check_admin_privileges(
    request: Request, 
    current_user: dict = Depends(get_current_user), 
    db: AsyncSession = Depends(async_get_db)
):
    """Check if current user has admin privileges"""
    # Force fresh database lookup to get latest superuser status
    from .crud.crud_users import crud_users
    
    fresh_user = await crud_users.get(db=db, username=current_user.get('username'))
    if fresh_user:
        # Check if fresh_user is a dict or model object
        if isinstance(fresh_user, dict):
            fresh_is_superuser = fresh_user.get("is_superuser", False)
        else:
            # It's a SQLAlchemy model object
            fresh_is_superuser = fresh_user.is_superuser
        
        # Update current_user with fresh superuser status
        current_user["is_superuser"] = fresh_is_superuser
        
        # Check if user is superuser
        is_superuser = current_user.get("is_superuser", False)
        
        if not is_superuser:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                {"error": "Access denied. Admin privileges required."}, 
                status_code=403
            )
        
        # User has admin privileges
        from fastapi.responses import JSONResponse
        return JSONResponse({"status": "success", "message": "Admin privileges confirmed"})
    
    # User not found
    from fastapi.responses import JSONResponse
    return JSONResponse(
        {"error": "User not found."}, 
        status_code=404
    )

@app.get("/admin_panel", response_class=HTMLResponse)
async def admin_panel(
    request: Request, 
    current_user: dict = Depends(get_current_user), 
    db: AsyncSession = Depends(async_get_db),
    project_page: int = Query(1, ge=1, description="Project page number"),
    scheduled_page: int = Query(1, ge=1, description="Scheduled posts page number"),
    per_page: int = Query(5, ge=1, le=20, description="Items per page"),
    project_filter: str = Query("", description="Filter projects by user ID"),
    scheduled_filter: str = Query("", description="Filter scheduled posts by user ID")
):
    print("[DEBUG] get_current_user called")
    print(f"[DEBUG] Admin panel accessed by user: {current_user.get('username', 'unknown')}")
    print(f"[DEBUG] User is_superuser: {current_user.get('is_superuser', False)}")
    print(f"[DEBUG] User ID: {current_user.get('id', 'unknown')}")
    print(f"[DEBUG] Full current_user dict: {current_user}")
    print(f"[DEBUG] Project filter: {project_filter}, Scheduled filter: {scheduled_filter}")
    
    # Force fresh database lookup to get latest superuser status
    from .crud.crud_users import crud_users
    from .core.security import create_access_token
    from datetime import timedelta
    from .core.config import settings
    
    fresh_user = await crud_users.get(db=db, username=current_user.get('username'))
    if fresh_user:
        # Check if fresh_user is a dict or model object
        if isinstance(fresh_user, dict):
            fresh_is_superuser = fresh_user.get("is_superuser", False)
            print(f"[DEBUG] Fresh database lookup (dict) - is_superuser: {fresh_is_superuser}")
        else:
            # It's a SQLAlchemy model object
            fresh_is_superuser = fresh_user.is_superuser
            print(f"[DEBUG] Fresh database lookup (model) - is_superuser: {fresh_is_superuser}")
        
        # Check if superuser status has changed
        original_is_superuser = current_user.get("is_superuser", False)
        if original_is_superuser != fresh_is_superuser:
            print(f"[DEBUG] Superuser status changed from {original_is_superuser} to {fresh_is_superuser}")
            # Force logout and redirect to login for fresh authentication
            from fastapi.responses import RedirectResponse
            response = RedirectResponse(url="/login", status_code=302)
            response.delete_cookie('access_token')
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
        
        # Update current_user with fresh superuser status
        current_user["is_superuser"] = fresh_is_superuser
        
        # Create new token with fresh data
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_token = await create_access_token(
            data={"sub": current_user["username"]}, 
            expires_delta=access_token_expires
        )
        print(f"[DEBUG] Created new token for user: {current_user['username']}")
        
        # Check if user is superuser - more robust check
        is_superuser = current_user.get("is_superuser", False)
        print(f"[DEBUG] Superuser check - User: {current_user.get('username', 'unknown')}, is_superuser: {is_superuser}, type: {type(is_superuser)}")
        
        if not is_superuser:
            print(f"[DEBUG] Access denied for user {current_user.get('username', 'unknown')} - not a superuser")
            # Check if this is an AJAX request
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                # Return JSON response for AJAX requests
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    {"error": "Access denied. Admin privileges required."}, 
                    status_code=403
                )
            else:
                # Return HTML response for regular requests
                return HTMLResponse("Access denied. Admin privileges required.", status_code=403)
        
        print(f"[DEBUG] Access granted for superuser {current_user.get('username', 'unknown')}")
        
        try:
            # Fetch all users
            print("[DEBUG] Fetching users from database...")
            result = await db.execute(select(User))
            db_users = result.scalars().all()
            users = []
            for user in db_users:
                users.append({
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_superuser": user.is_superuser
                })
            print(f"[DEBUG] Found {len(users)} users")
            
            # Fetch projects with pagination and filtering
            print("[DEBUG] Fetching projects from database...")
            from sqlalchemy import func
            offset_projects = (project_page - 1) * per_page
            
            # Build project query with optional user filtering
            project_query = select(Project)
            if project_filter and project_filter.strip():
                try:
                    user_id = int(project_filter)
                    project_query = project_query.where(Project.created_by_user_id == user_id)
                    print(f"[DEBUG] Filtering projects by user ID: {user_id}")
                except ValueError:
                    print(f"[DEBUG] Invalid project filter value: {project_filter}")
            
            # Get total count for pagination
            total_projects_result = await db.execute(select(func.count()).select_from(project_query.subquery()))
            total_projects = total_projects_result.scalar()
            
            # Get paginated projects
            result = await db.execute(
                project_query
                .order_by(Project.id.desc())
                .offset(offset_projects)
                .limit(per_page)
            )
            db_projects = result.scalars().all()
            projects = []
            for project in db_projects:
                # Get user info for this project
                user_result = await db.execute(select(User).where(User.id == project.created_by_user_id))
                user = user_result.scalar_one_or_none()
                projects.append({
                    "id": project.id,
                    "name": project.name,
                    "topic": project.topic,
                    "status": project.status,
                    "social_medias": project.social_medias,
                    "with_image": project.with_image,
                    "image_path": project.image_path,
                    "content_type": project.content_type,
                    "created_by_user_id": project.created_by_user_id,
                    "user_username": user.username if user else "Unknown"
                })
            print(f"[DEBUG] Found {len(projects)} projects (page {project_page})")
            
            # Fetch scheduled posts with pagination and filtering
            print("[DEBUG] Fetching scheduled posts from database...")
            offset_scheduled = (scheduled_page - 1) * per_page
            
            # Build scheduled posts query with optional user filtering
            scheduled_query = select(ScheduledPost)
            if scheduled_filter and scheduled_filter.strip():
                try:
                    user_id = int(scheduled_filter)
                    # Join with Project to filter by user
                    scheduled_query = scheduled_query.join(Project, ScheduledPost.project_id == Project.id)
                    scheduled_query = scheduled_query.where(Project.created_by_user_id == user_id)
                    print(f"[DEBUG] Filtering scheduled posts by user ID: {user_id}")
                except ValueError:
                    print(f"[DEBUG] Invalid scheduled filter value: {scheduled_filter}")
            
            # Get total count for pagination
            total_scheduled_result = await db.execute(select(func.count()).select_from(scheduled_query.subquery()))
            total_scheduled = total_scheduled_result.scalar()
            
            # Get paginated scheduled posts
            result = await db.execute(
                scheduled_query
                .order_by(ScheduledPost.id.desc())
                .offset(offset_scheduled)
                .limit(per_page)
            )
            db_scheduled_posts = result.scalars().all()
            scheduled_posts = []
            for scheduled_post in db_scheduled_posts:
                # Get project and user info for this scheduled post
                if scheduled_post.project_id:
                    project_result = await db.execute(select(Project).where(Project.id == scheduled_post.project_id))
                    project = project_result.scalar_one_or_none()
                    if project:
                        user_result = await db.execute(select(User).where(User.id == project.created_by_user_id))
                        user = user_result.scalar_one_or_none()
                        scheduled_posts.append({
                            "id": scheduled_post.id,
                            "project_id": scheduled_post.project_id,
                            "platforms": scheduled_post.platforms,
                            "scheduled_time": scheduled_post.scheduled_time.isoformat() if scheduled_post.scheduled_time else None,
                            "status": scheduled_post.status,
                            "user_id": project.created_by_user_id,
                            "user_username": user.username if user else "Unknown"
                        })
            print(f"[DEBUG] Found {len(scheduled_posts)} scheduled posts (page {scheduled_page})")
            
            print("[DEBUG] Rendering admin panel template...")
            response = templates.TemplateResponse("admin_panel.html", {
                "request": request,
                "users": users,
                "projects": projects,
                "scheduled_posts": scheduled_posts,
                "current_user": current_user,
                "username": current_user.get('username'),
                "project_page": project_page,
                "scheduled_page": scheduled_page,
                "per_page": per_page,
                "total_projects": total_projects,
                "total_scheduled": total_scheduled,
                "total_project_pages": (total_projects + per_page - 1) // per_page,
                "total_scheduled_pages": (total_scheduled + per_page - 1) // per_page,
                "project_filter": project_filter,
                "scheduled_filter": scheduled_filter
            })
            # Set new token in response
            response.set_cookie('access_token', new_token, httponly=True, samesite='Lax')
            # Add cache control headers to prevent caching
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
        except Exception as e:
            print(f"[ERROR] Error in admin panel: {str(e)}")
            return HTMLResponse(f"Error loading admin panel: {str(e)}", status_code=500)

@app.post("/admin_panel", response_class=HTMLResponse, include_in_schema=False)
async def admin_panel_post(request: Request, current_user=Depends(get_current_user)):
    # Simple superuser check
    if not current_user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="You do not have enough privileges.")
    
    print(f"[DEBUG] Admin panel POST accessed by user: {current_user.get('username')}")
    
    try:
        # Get form data
        form_data = await request.form()
        project_id = form_data.get('project_id')
        platforms = form_data.get('platforms', '').split(',')
        scheduled_time = form_data.get('scheduled_time')
        
        print(f"[DEBUG] Scheduling project - ID: {project_id}, Platforms: {platforms}, Time: {scheduled_time}")
        
        if not project_id:
            print("[DEBUG] No project_id provided")
            return RedirectResponse(url="/admin_panel", status_code=302)
        
        # Convert local time to IST (UTC+5:30) like the working schedule button
        from datetime import datetime
        local_date = datetime.fromisoformat(scheduled_time)
        pad = lambda n: f"0{n}" if n < 10 else str(n)
        ist_offset = '+05:30'
        ist_string = (f"{local_date.year}-"
                     f"{pad(local_date.month)}-"
                     f"{pad(local_date.day)}T"
                     f"{pad(local_date.hour)}:"
                     f"{pad(local_date.minute)}:"
                     f"{pad(local_date.second)}{ist_offset}")
        
        # Prepare payload in the correct format
        payload = {
            "scheduled_time": ist_string
        }
        
        # Make API call to the correct endpoint
        API_URL = "http://127.0.0.1:8000/api/v1"
        token = request.cookies.get('access_token')
        headers = get_headers(token)
        
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Use the correct endpoint that matches the working schedule button
                resp = await client.post(f"{API_URL}/tasks/projects/{project_id}/schedule", json=payload, headers=headers)
                print(f"[DEBUG] Schedule project response status: {resp.status_code}")
                print(f"[DEBUG] Schedule project response text: {resp.text}")
                
                if resp.status_code == 200 or resp.status_code == 202:
                    print("[DEBUG] Project scheduled successfully")
                    # Redirect back to admin panel with success
                    return RedirectResponse(url="/admin_panel", status_code=302)
                else:
                    print(f"[DEBUG] Failed to schedule project: {resp.text}")
                    # Redirect back to admin panel with error
                    return RedirectResponse(url="/admin_panel", status_code=302)
        except Exception as api_error:
            print(f"[DEBUG] API call error: {str(api_error)}")
            # Redirect back to admin panel with error
            return RedirectResponse(url="/admin_panel", status_code=302)
            
    except Exception as e:
        print(f"[ERROR] Error scheduling project: {str(e)}")
        return RedirectResponse(url="/admin_panel", status_code=302)

@app.get("/create_project", response_class=HTMLResponse, include_in_schema=False, name="create_project")
async def create_project_page(request: Request, current_user=Depends(get_current_user)):
    return templates.TemplateResponse("create_project.html", {
        "request": request, 
        "current_user": current_user,
        "username": current_user.get('username')
    })

@app.get("/show_projects", include_in_schema=False)
async def show_projects(request: Request, current_user=Depends(get_current_user)):
    return RedirectResponse(url="/user_panel")

@app.post("/projects/{project_id}/schedule", include_in_schema=False)
async def schedule_post(project_id: int, request: Request, current_user=Depends(get_current_user)):
    API_URL = "http://127.0.0.1:8000/api/v1"
    token = request.cookies.get('access_token')
    headers = get_headers(token)
    
    form_data = await request.form()
    platforms = form_data.get('platforms', '').split(',')
    scheduled_time = form_data.get('scheduled_time', '')
    
    # Convert scheduled_time to ISO format if needed
    if 'T' in scheduled_time:
        scheduled_time = scheduled_time.replace('T', ' ')
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{API_URL}/projects/{project_id}/schedule",
                json={"platforms": platforms, "scheduled_time": scheduled_time},
                headers=headers
            )
            
            if resp.status_code == 200:
                return RedirectResponse(url=f"/review_project/{project_id}", status_code=302)
            else:
                return RedirectResponse(url=f"/review_project/{project_id}", status_code=302)
    except Exception as e:
        print(f"[DEBUG] Schedule API error: {str(e)}")
        return RedirectResponse(url=f"/review_project/{project_id}", status_code=302)

@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False, name="dashboard")
async def dashboard(request: Request, current_user=Depends(get_optional_user), db: AsyncSession = Depends(async_get_db)):
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
       
    # Get projects directly from database instead of making HTTP request
    from .models.project import Project
    from sqlalchemy import select
    
    try:
        result = await db.execute(
            select(Project).where(Project.created_by_user_id == current_user["id"])
        )
        projects = result.scalars().all()
        print("DASHBOARD STATS: Number of projects =", len(projects), flush=True)
        # Convert to list of dicts for template
        projects_data = []
        for project in projects:
            projects_data.append({
                "id": project.id,
                "name": project.name,
                "topic": project.topic,
                "status": project.status,
                "social_medias": project.social_medias,
                "with_image": project.with_image,
                "image_path": project.image_path
            })
        
        # Calculate statistics for dashboard cards
        total_projects = len(projects)
        scheduled_projects = sum(1 for p in projects if p.status and p.status.lower() == "pending")
        posted_projects = sum(1 for p in projects if p.status and p.status.lower() == "posted")
        failed_projects = sum(1 for p in projects if p.status and p.status.lower() == "failed")
        print("DASHBOARD STATS:", total_projects, scheduled_projects, posted_projects, failed_projects)
        return templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "current_user": current_user, 
            "username": current_user.get('username'), 
            "projects": projects_data, 
            "API_URL": "http://127.0.0.1:8000/api/v1",
            "total_projects": total_projects,
            "scheduled_projects": scheduled_projects,
            "posted_projects": posted_projects,
            "failed_projects": failed_projects
        })
    except Exception as e:
        print("DASHBOARD ERROR:", e, flush=True)
        # If there's an error, return empty projects list
        return templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "current_user": current_user, 
            "username": current_user.get('username'), 
            "projects": [], 
            "API_URL": "http://127.0.0.1:8000/api/v1"
        })
        

@app.get("/review_project/{project_id}", response_class=HTMLResponse, include_in_schema=False, name="review_project")
async def review_project(project_id: int, request: Request, current_user=Depends(get_current_user)):
    API_URL = "http://127.0.0.1:8000/api/v1"
    token = request.cookies.get('access_token')
    headers = get_headers(token)
    
    # Fetch project details
    project_resp = requests.get(f"{API_URL}/projects/{project_id}", headers=headers)
    if project_resp.status_code != 200:
        return RedirectResponse(url="/dashboard", status_code=302)
    project = project_resp.json()
    
    # Fetch posts for the project
    posts_resp = requests.get(f"{API_URL}/projects/{project_id}/posts", headers=headers)
    posts = posts_resp.json().get('items', []) if posts_resp.status_code == 200 else []
    
    # Fetch scheduled posts for the project
    sched_resp = requests.get(f"{API_URL}/projects/{project_id}/scheduled_posts", headers=headers)
    scheduled_posts = sched_resp.json().get('items', []) if sched_resp.status_code == 200 else []
    
    return templates.TemplateResponse("review_project.html", {
        "request": request, 
        "project": project, 
        "posts": posts, 
        "scheduled_posts": scheduled_posts,
        "username": current_user.get('username')
    })

@app.get("/media_library", response_class=HTMLResponse, include_in_schema=False, name="media_library")
async def media_library_page(request: Request, current_user=Depends(get_current_user)):
    return templates.TemplateResponse("media_library.html", {
        "request": request,
        "username": current_user.get('username')
    })

@app.get("/analytics", response_class=HTMLResponse, include_in_schema=False, name="analytics")
async def analytics_dashboard(request: Request, current_user=Depends(get_current_user), db: AsyncSession = Depends(async_get_db)):
    """Analytics dashboard page"""
    # Get user's projects for the project selector
    projects_query = select(Project).where(Project.created_by_user_id == current_user["id"])
    result = await db.execute(projects_query)
    projects = result.scalars().all()
    
    return templates.TemplateResponse("analytics_dashboard.html", {
        "request": request, 
        "current_user": current_user,
        "username": current_user.get('username'),
        "projects": projects
    })

@app.get("/credentials")
async def credentials_management_page():
    """Serve the credentials management page"""
    return templates.TemplateResponse("credentials_management.html", {"request": {}})

app.include_router(api_v1_router)
app.include_router(posts_router, prefix="/api/v1/posts")
app.include_router(project.router, prefix="/api/v1")
app.include_router(scheduled_tasks.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(media.router)

@app.get("/test-static")
def test_static(request: Request):
    return {"static_url": request.url_for("static", filename="css/glass.css")}

@app.get("/test-media")
def test_media():
    return {"message": "Media system is working", "status": "ok"}

@app.get("/debug/routes")
def debug_routes():
    routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "methods": getattr(route, 'methods', []),
                "name": getattr(route, 'name', 'No name')
            })
    return {"routes": routes}

@app.get("/projects/create")
def redirect_projects_create():
    return RedirectResponse(url="/api/v1/projects/create")
