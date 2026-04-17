import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime

app = FastAPI()

# تحديد المسار بدقة لضمان العثور على مجلد templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, date: str = None, start_h: str = "06:00", end_h: str = "18:00"):
    now = datetime.now()
    target_date = date if date else now.strftime('%Y-%m-%d')
    
    # محاولة جلب البيانات مع حماية من الأخطاء
    gaps = []
    total_flights = 0
    
    try:
        url = "https://www.kaia.sa/ext-api/flightsearch/flights"
        headers = {"Authorization": "Basic dGVzdGVyOlRoZVMzY3JldA==", "User-Agent": "Mozilla/5.0"}
        
        # تجهيز أوقات البحث
        iso_start = f"{target_date}T{start_h}:00.000+03:00"
        iso_end = f"{target_date}T{end_h}:00.000+03:00"
        
        params = {
            "$filter": f"(EarlyOrDelayedDateTime ge {iso_start} and EarlyOrDelayedDateTime lt {iso_end}) and tolower(FlightNature) eq 'arrival' and Terminal eq 'T1'",
            "$orderby": "EarlyOrDelayedDateTime"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        data = response.json().get('value', [])
        
        flight_times = []
        for f in data:
            raw_time = f.get('EarlyOrDelayedDateTime')
            if raw_time:
                dt_obj = datetime.fromisoformat(raw_time.split('+')[0])
                flight_times.append(dt_obj)
        
        flight_times.sort()
        total_flights = len(flight_times)
        
        for i in range(len(flight_times) - 1):
            diff = (flight_times[i+1] - flight_times[i]).total_seconds() / 60
            if diff > 15:
                gaps.append({
                    'from': flight_times[i].strftime('%H:%M'),
                    'to': flight_times[i+1].strftime('%H:%M'),
                    'duration': int(diff)
                })
    except Exception as e:
        print(f"Error occurred: {e}")

    # إرجاع الصفحة حتى لو لم تتوفر بيانات لتجنب 500 Error
    return templates.TemplateResponse("index.html", {
        "request": request,
        "gaps": gaps,
        "date": target_date,
        "start_h": start_h,
        "end_h": end_h,
        "total": total_flights
    })
