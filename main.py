import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
import jinja2 # تأكيد استيراد المحرك

app = FastAPI()

# تعريف المسارات بشكل صارم
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=template_path)

class FlightAnalyzer:
    def __init__(self):
        self.url = "https://www.kaia.sa/ext-api/flightsearch/flights"
        self.headers = {
            "Accept": "application/json",
            "Authorization": "Basic dGVzdGVyOlRoZVMzY3JldA==",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def fetch_data(self, start_dt, end_dt):
        params = {
            "$filter": f"(EarlyOrDelayedDateTime ge {start_dt} and EarlyOrDelayedDateTime lt {end_dt}) and PublicRemark/Code ne 'NOP' and tolower(FlightNature) eq 'arrival' and Terminal eq 'T1' and (tolower(InternationalStatus) eq 'international')",
            "$orderby": "EarlyOrDelayedDateTime",
            "$count": "true"
        }
        try:
            response = requests.get(self.url, params=params, headers=self.headers, timeout=25)
            if response.status_code == 200:
                return response.json().get('value', [])
            return []
        except Exception as e:
            print(f"Fetch Error: {e}")
            return []

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, date: str = None, start_h: str = "06:00", end_h: str = "18:00"):
    analyzer = FlightAnalyzer()
    now = datetime.now()
    
    # ضمان وجود قيم افتراضية إذا كانت المدخلات فارغة
    current_date = date if date and date.strip() else now.strftime('%Y-%m-%d')
    s_time = start_h if start_h and start_h.strip() else "06:00"
    e_time = end_h if end_h and end_h.strip() else "18:00"
    
    # تجهيز التوقيت ISO
    iso_start = f"{current_date}T{s_time}:00.000+03:00"
    iso_end = f"{current_date}T{e_time}:00.000+03:00"
    
    data = analyzer.fetch_data(iso_start, iso_end)
    flight_times = []
    gaps = []

    if data:
        for f in data:
            status_info = f.get('PublicRemark')
            status_code = status_info.get('Code', '').upper() if status_info else ''
            
            # استبعاد الرحلات التي وصلت
            if status_code in ['ARR', 'DLV', 'LND']: 
                continue
            
            raw_time = f.get('EarlyOrDelayedDateTime')
            if raw_time:
                try:
                    dt_str = raw_time.split('+')[0]
                    dt_obj = datetime.fromisoformat(dt_str)
                    flight_times.append(dt_obj)
                except:
                    continue

    flight_times.sort()
    
    for i in range(len(flight_times) - 1):
        diff = (flight_times[i+1] - flight_times[i]).total_seconds() / 60
        if diff > 15:
            gaps.append({
                'from': flight_times[i].strftime('%H:%M'),
                'to': flight_times[i+1].strftime('%H:%M'),
                'duration': int(diff)
            })

    # إرسال البيانات للـ HTML
    return templates.TemplateResponse("index.html", {
        "request": request,
        "gaps": gaps,
        "date": current_date,
        "start_h": s_time,
        "end_h": e_time,
        "total": len(flight_times)
    })
