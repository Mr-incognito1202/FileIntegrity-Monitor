import hashlib
import json
import os
import sys

BASELINE_FILE = "baseline.json"


def calculate_sha256(file_path):
  """Calculates SHA-256 hash using chunked streaming."""
  sha256_hash = hashlib.sha256()
  try:
    with open(file_path, "rb") as f:
      while True:
        data = f.read(65536)
        if not data:
          break
        sha256_hash.update(data)
    return sha256_hash.hexdigest()
  except (PermissionError, FileNotFoundError) as e:
    print(f"[!] Access error on {file_path}: {e}")
    return None


def scan_directory(directory_path):
  """Walks the folder and returns path-to-hash mappings."""
  collected = {}
  for root, dirs, files in os.walk(directory_path):
    for file_name in files:
      file_path = os.path.join(root, file_name)
      norm_path = os.path.normpath(file_path)
      file_hash = calculate_sha256(norm_path)
      if file_hash:
        collected[norm_path] = file_hash
  return collected


def create_baseline(directory_path):
  """Generates baseline.json snapshot."""
  if not os.path.isdir(directory_path):
    print(f"[-] Directory '{directory_path}' does not exist.")
    return

  print(f"[*] Scanning '{directory_path}' to generate baseline...")
  scan_results = scan_directory(directory_path)

  with open(BASELINE_FILE, "w", encoding="utf-8") as f:
    json.dump(scan_results, f, indent=4)

  print(f"[+] Baseline successfully generated with {len(scan_results)} files.")
  print(f"[+] Saved to: {os.path.abspath(BASELINE_FILE)}\n")


def verify_integrity(directory_path):
  """Verifies live files against baseline.json."""
  if not os.path.exists(BASELINE_FILE):
    print(f"[-] Baseline '{BASELINE_FILE}' not found. Generate one first.")
    return

  with open(BASELINE_FILE, "r", encoding="utf-8") as f:
    baseline = json.load(f)

  print(f"[*] Auditing '{directory_path}' against baseline...")
  current_state = scan_directory(directory_path)

  intact = 0
  tampered = 0
  deleted = 0
  rogue = 0
  for path, expected_hash in baseline.items():
    if path not in current_state:
      print(f"[-] DELETED: {path}")
      deleted += 1
    elif current_state[path] != expected_hash:
      print(f"[!] TAMPERED: {path}")
      print(f"    Expected: {expected_hash}")
      print(f"    Observed: {current_state[path]}")
      tampered += 1
    else:
      intact += 1

  for live_p in current_state:
    if live_p not in baseline:
      print(f"[+] NEW / ROGUE: {live_p}")
      rogue += 1

  print("\n" + "=" * 45)
  print(
      f"SUMMARY: Intact: {intact} | Tampered: {tampered} | Deleted: {deleted} |"
      f" Rogue: {rogue}"
  )
  print("=" * 45)
if __name__ == "__main__":
  print("=== File Integrity Monitor (CLI Engine) ===")
  print("1. Create Baseline Snapshot")
  print("2. Verify Integrity Against Baseline")
  choice = input("Select an option (1 or 2): ").strip()

  raw_dir = input("Enter directory path: ").strip(' "\'')
  abs_dir = os.path.abspath(raw_dir)

  if choice == "1":
    create_baseline(abs_dir)
  elif choice == "2":
    verify_integrity(abs_dir)
  else:
    print("[-] Invalid choice.")