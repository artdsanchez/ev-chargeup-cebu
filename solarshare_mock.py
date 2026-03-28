"""
Mock server for testing SolarShare EV Cebu UI without Google Sheets.
Run: python solarshare_mock.py
Open: http://localhost:8766
"""
import http.server, json, os

PORT = 8766
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

MOCK_DATA = [
    {"name":"Mang Romy Bacalso",      "address":"Nivel Hills, Lahug, Cebu City",       "barangay":"Lahug",              "lat":10.3322,"lng":123.9050,"charger_type":"Solar",      "notes":"Solar-powered 7kW charger. Free for neighbors. Available daily 7am-3pm.","contact":"09171234567"},
    {"name":"Ate Marivic Santos",      "address":"Banilad Road, Banilad, Cebu City",    "barangay":"Banilad",            "lat":10.3410,"lng":123.9020,"charger_type":"Solar",      "notes":"Solar-powered charger. ₱5/kWh. Message first.","contact":"marivic@email.com"},
    {"name":"Kuya Felix Uy",           "address":"Gorordo Ave, Camputhaw, Cebu City",   "barangay":"Camputhaw",          "lat":10.3280,"lng":123.9100,"charger_type":"EV Charger", "notes":"Grid-powered 7kW charger. ₱8/kWh. Weekends only.","contact":"09209876543"},
    {"name":"Nang Cora Reyes",         "address":"F. Llamas St, Pardo, Cebu City",      "barangay":"Pardo",              "lat":10.2950,"lng":123.8900,"charger_type":"Solar",      "notes":"Solar-powered charger. Free for the barangay. Just knock!","contact":"09151112222"},
    {"name":"Dodong Caballero",        "address":"Mactan Island, Lapu-Lapu City",       "barangay":"Pusok (Lapu-Lapu)",  "lat":10.3050,"lng":123.9700,"charger_type":"EV Charger", "notes":"Grid-powered 7kW charger. Free for first 3 neighbors.","contact":"09063334444"},
    {"name":"Inday Lorna Delos Reyes", "address":"Talamban Rd, Talamban, Cebu City",    "barangay":"Talamban",           "lat":10.3600,"lng":123.9150,"charger_type":"Solar",      "notes":"Solar-powered charger. ₱6/kWh. Contact to arrange.","contact":"lorna.delosreyes@gmail.com"},
    {"name":"Manong Eddie Villareal",  "address":"AS Fortuna St, Mandaue City",         "barangay":"Bakilid (Mandaue)",  "lat":10.3500,"lng":123.9350,"charger_type":"Solar",      "notes":"Solar-powered 11kW charger. ₱6/kWh. 8am-3pm daily.","contact":"09175556666"},
    {"name":"Aling Perla Flores",      "address":"Talisay City, near SRP",              "barangay":"San Isidro (Talisay)","lat":10.2450,"lng":123.8480,"charger_type":"EV Charger","notes":"Grid-powered charger. Free for barangay residents. Others ₱4/kWh.","contact":"09227778888"},
]

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PROJECT_DIR, **kwargs)

    def do_GET(self):
        if self.path in ('/', '/solarshare'):
            self.path = '/solarshare.html'; return super().do_GET()
        if self.path == '/listings':
            body = json.dumps(MOCK_DATA).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        return super().do_GET()

    def do_POST(self):
        if self.path == '/listings':
            length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(length))
            MOCK_DATA.append({**data, "date_added": "2026-03-27"})
            print(f"  [mock] New listing: {data.get('name')} — {data.get('barangay')}")
            body = json.dumps({"status": "ok"}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404); self.end_headers()

    def log_message(self, format, *args): pass

if __name__ == '__main__':
    print(f"Mock server running at http://localhost:{PORT}  (Ctrl+C to stop)")
    http.server.HTTPServer(('localhost', PORT), Handler).serve_forever()
