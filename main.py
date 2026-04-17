import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()

# إعداد المسارات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # بيانات وهمية للتجربة فقط
    test_gaps = [
        {'from': '10:00', 'to': '10:45', 'duration': 45},
        {'from': '14:20', 'to': '15:00', 'duration': 40}
    ]
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "gaps": test_gaps,
        "date": "2026-04-17",
        "start_h": "06:00",
        "end_h": "18:00",
        "total": 2
    })
