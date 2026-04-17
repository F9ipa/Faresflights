import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

class FlightAnalyzer:
    def __init__(self):
        self.url = "https://www.kaia.sa/ext-api/flightsearch/flights"
        self.headers = {
            "Accept": "application/json",
            "Authorization": "Basic dGVzdGVyOlRoZVMzY3JldA==",
            "User-Agent": "Mozilla/5.0"
        }

    def fetch_data(self, start_dt, end_dt):
        params = {
            "$filter": f"(EarlyOrDelayedDateTime ge {start_dt} and EarlyOrDelayedDateTime lt {end_dt}) and PublicRemark/Code ne 'NOP' and tolower(FlightNature) eq 'arrival' and Terminal eq 'T1' and (tolower(InternationalStatus) eq 'international')",
            "$orderby": "EarlyOrDelayedDateTime",
            "$count": "true"
        }
        try:
            response = requests.get(self.url, params=params, headers=self.headers, timeout=20)
            return response.json().get('value', [])
        except: return []

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, date: str = None, start_h: str = "06:00", end_h: str = "18:00"):
    analyzer = FlightAnalyzer()
    now = datetime.now()
    
    # استخدام التاريخ المدخل أو تاريخ اليوم
    target_date = date or now.strftime('%Y-%m-%d')
    
    # تجهيز التوقيت بتنسيق ISO لموقع المطار
    iso_start = f"{target_date}T{start_h}:00.000+03:00"
    iso_end = f"{target_date}T{end_h}:00.000+03:00"
    
    data = analyzer.fetch_data(iso_start, iso_end)
    flight_times = []
    gaps = []

    for f in data:
        status_code = f.get('PublicRemark', {}).get('Code', '').upper()
        if status_code in ['ARR', 'DLV', 'LND']: continue
        
        try:
            dt_raw = f.get('EarlyOrDelayedDateTime').split('+')[0]
            dt_obj = datetime.fromisoformat(dt_raw)
            flight_times.append(dt_obj)
        except: continue

    flight_times.sort()
    for i in range(len(flight_times) - 1):
        diff = (flight_times[i+1] - flight_times[i]).total_seconds() / 60
        if diff > 15:
            gaps.append({'from': flight_times[i].strftime('%H:%M'), 'to': flight_times[i+1].strftime('%H:%M'), 'duration': int(diff)})

    return templates.TemplateResponse("index.html", {
        "request": request, "gaps": gaps, "date": target_date, 
        "start_h": start_h, "end_h": end_h, "total": len(flight_times)
    })
