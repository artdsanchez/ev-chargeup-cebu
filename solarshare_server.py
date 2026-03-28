"""
SolarShare EV Cebu server.
Serves solarshare.html and handles listing reads/writes via Google Sheets.

Setup:
  1. Create a Google Sheet, add a tab named "Listings"
  2. Share it with your service account email (in credentials.json)
  3. Paste the Sheet ID into SPREADSHEET_ID below
  4. Run: python solarshare_server.py
  5. Open: http://localhost:8766
"""

import http.server
import json
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlparse, parse_qs, quote
import gspread
from datetime import datetime

# Load .env file if present (local development)
_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(_env):
    for _line in open(_env):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

GMAIL_USER         = os.environ.get("GMAIL_USER", "shanes.solar.solutions@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

PORT = int(os.environ.get("PORT", 8766))
BASE_URL = os.environ.get("BASE_URL", f"http://localhost:{os.environ.get('PORT', '8766')}")
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.environ.get("CREDENTIALS_FILE", os.path.join(PROJECT_DIR, "credentials.json"))

SPREADSHEET_ID = "1xwqi4cldEuBMpIZ-9IZ7AT3rWEqxeDAnX3Lc7N5SJKg"
SHEET_TAB = "Listings"

HEADERS = ["name", "address", "barangay", "lat", "lng", "charger_type", "power_kw", "pricing", "days", "hours", "notes", "email", "phone", "facebook", "date_added", "approved"]

PRIVATE_FIELDS = {"email", "phone", "facebook"}


def get_worksheet():
    gc = gspread.service_account(filename=CREDENTIALS_FILE)
    sh = gc.open_by_key(SPREADSHEET_ID)
    ws = sh.worksheet(SHEET_TAB)
    # Auto-create headers if sheet is empty
    if not ws.row_values(1):
        ws.append_row(HEADERS)
    return ws


def send_notification(to_email, owner_name, sender_name, sender_email, sender_phone, message):
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = "New charging request on EV-ChargeUp Cebu"
    msg.attach(MIMEText(f"""Hi {owner_name},

Someone is interested in your EV charger listing on EV-ChargeUp Cebu.

From: {sender_name}
Mobile: {sender_phone}
Email: {sender_email}

Message:
{message}

Reply directly to {sender_email} or call/text {sender_phone} to get in touch.

— EV-ChargeUp Cebu
""", "plain"))
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, to_email, msg.as_string())


def send_admin_notification(listing, approve_url):
    name = listing.get("name", "")
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = GMAIL_USER
    msg["Subject"] = f"New listing pending approval — {name}"
    msg.attach(MIMEText(f"""New listing submitted on EV-ChargeUp Cebu and is waiting for your approval.

Owner:    {name}
Address:  {listing.get('address', '')}, {listing.get('barangay', '')}
Charger:  {listing.get('charger_type', '')} — {listing.get('power_kw', '')}
Pricing:  {listing.get('pricing', '')}
Days:     {listing.get('days', '')}
Hours:    {listing.get('hours', '')}
Email:    {listing.get('email', '')}
Phone:    {listing.get('phone', '')}

To approve and publish this listing, click the link below:
{approve_url}

— EV-ChargeUp Cebu
""", "plain"))
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())


def send_owner_approval(to_email, owner_name):
    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = "Your listing is now live on EV-ChargeUp Cebu!"
    msg.attach(MIMEText(f"""Hi {owner_name},

Great news! Your EV charger listing has been approved and is now live on EV-ChargeUp Cebu.

EV drivers in Cebu can now find your listing on the map and send you charging requests.

Thank you for being part of the community!

— EV-ChargeUp Cebu
""", "plain"))
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, to_email, msg.as_string())


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PROJECT_DIR, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        clean = urlparse(self.path).path  # strip ?fbclid=... and other query params

        # Block direct access to sensitive files
        blocked = {"/credentials.json", "/.env"}
        if clean in blocked or clean.endswith(".py"):
            self.send_response(403)
            self.end_headers()
            return

        if clean in ("/", "/solarshare"):
            self.path = "/solarshare.html"
            return super().do_GET()

        if clean == "/listings":
            self._serve_listings()
            return

        if clean.startswith("/approve"):
            self._handle_approve()
            return

        return super().do_GET()

    def do_POST(self):
        if self.path == "/listings":
            self._add_listing()
            return
        if self.path == "/contact":
            self._handle_contact()
            return
        self.send_response(404)
        self.end_headers()

    def _serve_listings(self):
        try:
            ws = get_worksheet()
            records = ws.get_all_records()
            safe = []
            for r in records:
                r["lat"] = float(r.get("lat") or 0)
                r["lng"] = float(r.get("lng") or 0)
                safe.append({k: v for k, v in r.items() if k not in PRIVATE_FIELDS})
            self._json(200, safe)
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _add_listing(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            ws = get_worksheet()
            ws.append_row([
                body.get("name", "").strip(),
                body.get("address", "").strip(),
                body.get("barangay", "").strip(),
                float(body.get("lat", 0)),
                float(body.get("lng", 0)),
                body.get("charger_type", "Both").strip(),
                body.get("power_kw", "").strip(),
                body.get("pricing", "").strip(),
                body.get("days", "").strip(),
                body.get("hours", "").strip(),
                body.get("notes", "").strip(),
                body.get("email", "").strip(),
                body.get("phone", "").strip(),
                body.get("facebook", "").strip(),
                datetime.now().strftime("%Y-%m-%d"),
                "No",
            ])
            approve_url = f"{BASE_URL}/approve?name={quote(body.get('name', '').strip())}"
            send_admin_notification(body, approve_url)
            self._json(200, {"status": "ok"})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _handle_contact(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            owner_name   = body.get("owner_name", "").strip()
            sender_name  = body.get("sender_name", "").strip()
            sender_email = body.get("sender_email", "").strip()
            sender_phone = body.get("sender_phone", "").strip()
            message      = body.get("message", "").strip()
            if not all([owner_name, sender_name, sender_email, sender_phone, message]):
                self._json(400, {"error": "All fields are required."}); return
            ws = get_worksheet()
            records = ws.get_all_records()
            owner = next((r for r in records if r.get("name", "").strip().lower() == owner_name.lower()), None)
            if not owner or not owner.get("email"):
                self._json(404, {"error": "Owner not found."}); return
            send_notification(owner["email"], owner_name, sender_name, sender_email, sender_phone, message)
            self._json(200, {"status": "ok"})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_approve(self):
        try:
            params = parse_qs(urlparse(self.path).query)
            name = params.get("name", [""])[0].strip()
            if not name:
                self._html(400, "<h1>Missing listing name.</h1>"); return
            ws = get_worksheet()
            records = ws.get_all_records()
            row_idx = None
            owner_email = None
            already_approved = False
            for i, r in enumerate(records):
                if r.get("name", "").strip().lower() == name.lower():
                    row_idx = i + 2  # +2: header row + 0-index offset
                    owner_email = r.get("email", "")
                    already_approved = str(r.get("approved", "")).lower() == "yes"
                    break
            if not row_idx:
                self._html(404, self._page("Not Found", f"No listing found for <b>{name}</b>.")); return
            if already_approved:
                self._html(200, self._page("Already Live", f"<b>{name}</b>'s listing is already live on the map.")); return
            headers = ws.row_values(1)
            approved_col = headers.index("approved") + 1
            ws.update_cell(row_idx, approved_col, "Yes")
            if owner_email:
                send_owner_approval(owner_email, name)
            self._html(200, self._page("Approved!", f"<b>{name}</b>'s listing is now live on EV-ChargeUp Cebu.<br><br>The owner has been notified by email."))
        except Exception as e:
            self._html(500, self._page("Error", str(e)))

    def _page(self, title, body):
        return f"""<!DOCTYPE html><html><head><title>{title} — EV-ChargeUp Cebu</title>
        <style>body{{font-family:sans-serif;background:#0E0F0D;color:#EEEbE4;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}}
        .box{{text-align:center;padding:40px}}h2{{color:#22c97a;font-size:24px;margin-bottom:12px}}p{{color:#7a7e79;font-size:14px;line-height:1.6}}</style></head>
        <body><div class="box"><h2>&#9889; {title}</h2><p>{body}</p></div></body></html>"""

    def _html(self, code, content):
        body = content.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {args[0]} {args[1]}", flush=True)


if __name__ == "__main__":
    os.chdir(PROJECT_DIR)
    print(f"EV-ChargeUp Cebu running on port {PORT}", flush=True)
    http.server.HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
