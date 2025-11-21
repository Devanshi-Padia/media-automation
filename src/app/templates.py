import os
from fastapi.templating import Jinja2Templates

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
templates_dir = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=templates_dir)

def static_url(filename: str):
    return f"/static/{filename}"

templates.env.globals['static_url'] = static_url 