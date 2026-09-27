import hashlib
import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)


VT_API_KEY = "3a8e91ba4f9f938d1873ccd31ac8cbbf461db71e5b50958854adf5c945f6044a"

baseline_db = {}


def check_virustotal_hash(file_hash):
  """Checks the SHA-256 hash against VirusTotal.

  Returns a tuple: (status_text, malicious_count)
  """
  if not VT_API_KEY or VT_API_KEY == "YOUR_VIRUSTOTAL_API_KEY_HERE":
    return "API Key Missing", 0

  url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
  headers = {"x-apikey": VT_API_KEY}

  try:
    response = requests.get(url, headers=headers, timeout=5)
    if response.status_code == 200:
      data = response.json()
      stats = (
          data.get("data", {})
          .get("attributes", {})
          .get("last_analysis_stats", {})
      )
      malicious = stats.get("malicious", 0)
      suspicious = stats.get("suspicious", 0)
      total_threats = malicious + suspicious

      if total_threats > 0:
        return f"Malicious ({total_threats} vendors flagged)", total_threats
      return "Clean (0 flags)", 0
    elif response.status_code == 404:
      return "Unknown to VT (No threats reported)", 0
    elif response.status_code == 429:
      return "Rate Limit Exceeded", 0
    return f"VT Error ({response.status_code})", 0
  except requests.RequestException:
    return "VT Unreachable", 0

def get_file_type(filename):
  ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
  types = {
      "bat": "Batch Script",
      "cmd": "Command Script",
      "ps1": "PowerShell Script",
      "sh": "Shell Script",
      "py": "Python Script",
      "exe": "Executable Binary",
      "dll": "Dynamic Link Library",
      "txt": "Text File",
      "pdf": "PDF Document",
      "docx": "Word Document",
      "json": "JSON Data",
      "csv": "Spreadsheet Data",
      "png": "PNG Image",
      "jpg": "JPEG Image",
  }
  return types.get(ext, f"{ext.upper()} File" if ext else "Unknown File")


def format_size(size_in_bytes):
  if size_in_bytes < 1024:
    return f"{size_in_bytes} B"
  elif size_in_bytes < 1048576:
    return f"{round(size_in_bytes / 1024, 1)} KB"
  return f"{round(size_in_bytes / 1048576, 1)} MB"


def calculate_sha256_stream(file_stream):
  hasher = hashlib.sha256()
  while True:
    chunk = file_stream.read(65536)
    if not chunk:
      break
    hasher.update(chunk)
  file_stream.seek(0)
  return hasher.hexdigest()


@app.route("/")
def index():
  return app.send_static_file("index.html")


@app.route("/api/save-baseline", methods=["POST"])
def save_baseline():
  uploaded_files = request.files.getlist("files")
  if not uploaded_files:
    return jsonify({"error": "No files provided"}), 400

  baseline_db.clear()
  results = []

  for file in uploaded_files:
    file_hash = calculate_sha256_stream(file.stream)
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)

    filename = file.filename
    file_type = get_file_type(filename)
    size_str = format_size(size)


    vt_result, malicious_count = check_virustotal_hash(file_hash)

    baseline_db[filename] = {
        "hash": file_hash,
        "type": file_type,
        "size": size_str,
        "threat": vt_result,
        "is_threat": malicious_count > 0,
    }

    results.append({
        "name": filename,
        "type": file_type,
        "size": size_str,
        "hash": file_hash,
        "status": "Intact",
        "threat": vt_result,
        "is_threat": malicious_count > 0,
    })

  return jsonify({"message": "Baseline saved successfully", "files": results})


@app.route("/api/check-integrity", methods=["POST"])
def check_integrity():
  if not baseline_db:
    return (
        jsonify({
            "error": "No baseline found. Please click 'Save Baseline' first."
        }),
        400,
    )
  uploaded_files = request.files.getlist("files")
  if not uploaded_files:
    return jsonify({"error": "No files provided to check"}), 400

  results = []
  seen_files = set()

  for file in uploaded_files:
    filename = file.filename
    seen_files.add(filename)
    current_hash = calculate_sha256_stream(file.stream)

    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)

    file_type = get_file_type(filename)
    size_str = format_size(size)
    vt_result, malicious_count = check_virustotal_hash(current_hash)

    if filename not in baseline_db:
      status = "New"
    else:
      original_hash = baseline_db[filename]["hash"]
      status = "Intact" if current_hash == original_hash else "Modified"
    results.append({
        "name": filename,
        "type": file_type,
        "size": size_str,
        "hash": current_hash,
        "status": status,
        "threat": vt_result,
        "is_threat": malicious_count > 0,
    })
  for base_filename, base_info in baseline_db.items():
    if base_filename not in seen_files:
      results.append({
          "name": base_filename,
          "type": base_info["type"],
          "size": base_info["size"],
          "hash": "FILE DELETED / MISSING",
          "status": "Deleted",
          "threat": "N/A",
          "is_threat": False,
      })

  return jsonify({"files": results})
@app.route("/api/reset", methods=["POST"])
def reset():
  baseline_db.clear()
  return jsonify({"message": "Baseline cleared"})
if __name__ == "__main__":
  app.run(host="127.0.0.1", port=5000, debug=True)