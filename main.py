from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests
from datetime import datetime
from collections import Counter

app = FastAPI()
templates = Jinja2Templates(directory="templates")

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
            response = requests.get(self.url, params=params, headers=self.headers, timeout=10)
            return response.json().get('value', [])
        except:
            return []

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, day: str = None):
    analyzer = FlightAnalyzer()
    now = datetime.now()
    target_day = day or str(now.day)
    date_str = now.strftime(f'%Y-%m-{target_day.zfill(2)}')

    iso_start = f"{date_str}T06:00:00.000+03:00"
    iso_end = f"{date_str}T18:00:00.000+03:00"

    data = analyzer.fetch_data(iso_start, iso_end)
    flight_times = []
    gaps = []

    for f in data:
        status_code = f.get('PublicRemark', {}).get('Code', '').upper()
        if status_code in ['ARR', 'DLV', 'LND']:
            continue

        dt_raw = f.get('EarlyOrDelayedDateTime').split('+')[0]
        dt_obj = datetime.fromisoformat(dt_raw)
        flight_times.append(dt_obj)

    flight_times.sort()
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
