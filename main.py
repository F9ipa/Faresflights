import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime

app = FastAPI()

# --- حل مشكلة المسارات في السيرفر ---
# هذا الجزء يضمن أن السيرفر سيجد مجلد templates مهما كان نوع الاستضافة
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
            # زيادة وقت الانتظار لضمان استجابة موقع المطار
            response = requests.get(self.url, params=params, headers=self.headers, timeout=20)
            response.raise_for_status()
            return response.json().get('value', [])
        except Exception as e:
            print(f"Error fetching data: {e}")
            return []

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, day: str = None):
    analyzer = FlightAnalyzer()
    now = datetime.now()
    
    # تحديد اليوم الحالي أو المختار
    target_day = day or str(now.day)
    try:
        date_str = now.strftime(f'%Y-%m-{int(target_day):02d}')
    except:
        date_str = now.strftime('%Y-%m-%d')

    # تحديد فترة البحث (من الصباح حتى نهاية اليوم)
    iso_start = f"{date_str}T00:00:00.000+03:00"
    iso_end = f"{date_str}T23:59:59.000+03:00"
    
    data = analyzer.fetch_data(iso_start, iso_end)
    flight_times = []
    gaps = []

    for f in data:
        status = f.get('PublicRemark', {})
        status_code = status.get('Code', '').upper()
        
        # استبعاد الرحلات التي هبطت أو وصلت بالفعل
        if status_code in ['ARR', 'DLV', 'LND']:
            continue
        
        try:
            dt_raw = f.get('EarlyOrDelayedDateTime').split('+')[0]
            dt_obj = datetime.fromisoformat(dt_raw)
            flight_times.append(dt_obj)
        except:
            continue

    flight_times.sort()
    
    # حساب الفجوات الزمنية التي تزيد عن 15 دقيقة
    for i in range(len(flight_times) - 1):
        diff = (flight_times[i+1] - flight_times[i]).total_seconds() / 60
        if diff > 15:
            gaps.append({
                'from': flight_times[i].strftime('%H:%M'),
                'to': flight_times[i+1].strftime('%H:%M'),
                'duration': int(diff)
            })

    return templates.TemplateResponse("index.html", {
        "request": request, 
        "gaps": gaps, 
        "date": date_str,
        "total": len(flight_times)
    })
