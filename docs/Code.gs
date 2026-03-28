/**
 * SolarShare Cebu — Google Apps Script Backend
 *
 * HOW TO DEPLOY:
 *  1. Go to script.google.com → New project → paste this entire file
 *  2. Click "Deploy" → "New deployment" → Type: Web app
 *     - Execute as: Me
 *     - Who has access: Anyone
 *  3. Click Deploy → copy the Web App URL
 *  4. Run: ./deploy.sh <paste URL here>
 */

const SPREADSHEET_ID = "YOUR_SPREADSHEET_ID_HERE"; // paste your Google Sheet ID
const SHEET_TAB      = "Listings";
const HEADERS        = ["name","address","barangay","lat","lng","charger_type","power_kw","pricing","days","solar_excess","solar_price","notes","contact","date_added"];

function getSheet() {
  var sh = SpreadsheetApp.openById(SPREADSHEET_ID);
  var ws = sh.getSheetByName(SHEET_TAB);
  if (!ws) ws = sh.insertSheet(SHEET_TAB);
  if (ws.getLastRow() === 0) ws.appendRow(HEADERS);
  return ws;
}

// GET — returns all listings as JSON
function doGet(e) {
  try {
    var ws   = getSheet();
    var rows = ws.getDataRange().getValues();
    if (rows.length <= 1) {
      return json([]);
    }
    var headers = rows[0];
    var records = rows.slice(1).map(function(r) {
      var obj = {};
      headers.forEach(function(h, i) { obj[h] = r[i]; });
      obj.lat = parseFloat(obj.lat) || 0;
      obj.lng = parseFloat(obj.lng) || 0;
      return obj;
    }).filter(function(r) { return r.name; });
    return json(records);
  } catch(e) {
    return json({ error: e.toString() });
  }
}

// POST — appends a new listing (body sent as text/plain JSON)
function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var ws   = getSheet();
    ws.appendRow([
      (data.name         || "").toString().trim(),
      (data.address      || "").toString().trim(),
      (data.barangay     || "").toString().trim(),
      parseFloat(data.lat)  || 0,
      parseFloat(data.lng)  || 0,
      (data.charger_type || "Both").toString().trim(),
      (data.power_kw     || "").toString().trim(),
      (data.pricing      || "").toString().trim(),
      (data.days         || "").toString().trim(),
      (data.solar_excess || "").toString().trim(),
      (data.solar_price  || "").toString().trim(),
      (data.notes        || "").toString().trim(),
      (data.contact      || "").toString().trim(),
      new Date().toISOString().split("T")[0],
    ]);
    return json({ status: "ok" });
  } catch(e) {
    return json({ error: e.toString() });
  }
}

function json(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}
