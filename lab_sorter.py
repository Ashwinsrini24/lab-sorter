"""
Lab Booking Request Sorter
CIT AI-Native Engineering Programme · Semester 1 · Assessment 5

This program reads:
  1. labs.csv
  2. bookings.csv
  3. requests.csv

Extracts structured booking parameters using an LLM (with offline heuristic fallback),
validates facts, evaluates status cascading rules, and outputs:
  1. results.csv
  2. schedule.csv
  3. issues.csv
  4. summary.txt
"""

import os
import sys
import csv
import json
import re
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

# Academic semester boundary (Semester 1, 2026)
SEMESTER_START = datetime(2026, 10, 1)
SEMESTER_END = datetime(2026, 12, 31)

ALLOWED_FIELDS = ["lab", "date", "slot", "students", "summary"]


# ==========================================
# 1. Loading Functions (CSV I/O)
# ==========================================

def load_labs(filepath: str) -> Dict[str, Dict[str, Any]]:
    """Loads labs.csv into a dictionary keyed by lab code."""
    labs = {}
    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = row["code"].strip()
                name = row["name"].strip()
                capacity = int(row["capacity"].strip())
                labs[code] = {"name": name, "capacity": capacity}
    except Exception as e:
        print(f"Error loading labs from {filepath}: {e}")
        raise
    return labs


def load_bookings(filepath: str) -> set:
    """Loads existing confirmed bookings into a set of (date, slot, lab) tuples."""
    bookings = set()
    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row["date"].strip()
                slot = row["slot"].strip()
                lab = row["lab"].strip()
                bookings.add((date, slot, lab))
    except Exception as e:
        print(f"Error loading bookings from {filepath}: {e}")
        raise
    return bookings


def load_requests(filepath: str) -> List[Dict[str, str]]:
    """Loads raw booking requests from requests.csv."""
    requests = []
    try:
        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                requests.append({
                    "id": row["id"].strip(),
                    "sent": row["sent"].strip(),
                    "request": row["request"].strip()
                })
    except Exception as e:
        print(f"Error loading requests from {filepath}: {e}")
        raise
    return requests


# ==========================================
# 2. System Prompt & LLM Client
# ==========================================

def get_system_prompt() -> str:
    """Reads system_prompt.txt or returns embedded 5-role prompt."""
    prompt_path = os.path.join(os.path.dirname(__file__), "system_prompt.txt")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    return "You are an administrative scheduling parser extracting lab booking JSON."


def call_llm_api(prompt_text: str, request_text: str) -> Optional[str]:
    """
    Calls an external LLM API if GEMINI_API_KEY or GROQ_API_KEY is configured.
    API key is read strictly from environment variable, never hardcoded.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {
                "systemInstruction": {"parts": [{"text": prompt_text}]},
                "contents": [{"parts": [{"text": f"Extract booking JSON for this request: \"{request_text}\""}]}],
                "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"}
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text
        except Exception:
            pass

    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": prompt_text},
                    {"role": "user", "content": f"Extract booking JSON for this request: \"{request_text}\""}
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {groq_key}"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["choices"][0]["message"]["content"]
                return text
        except Exception:
            pass

    return None


def heuristic_fallback_parser(request_text: str) -> Dict[str, Any]:
    """
    Deterministic rule-based extractor adhering strictly to the spec.
    Used when LLM API is unavailable, fails, or replies with invalid JSON.
    """
    res = {
        "lab": None,
        "date": None,
        "slot": None,
        "students": None,
        "summary": ""
    }

    req_lower = request_text.lower()

    # Relative dates must be null
    is_relative = bool(re.search(r"\b(tomorrow|yesterday|today|next week|next friday|next monday)\b", req_lower))

    # Date extraction (YYYY-MM-DD or DD Month / Month DD)
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", request_text)
    if date_match and not is_relative:
        res["date"] = date_match.group(1)
    elif not is_relative:
        month_map = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
            "october": 10, "november": 11, "december": 12
        }
        text_date_match = re.search(r"(\b\d{1,2}(?:st|nd|rd|th)?\b)\s+(october|november|december|oct|nov|dec)", req_lower)
        if text_date_match:
            day_str = re.sub(r"\D", "", text_date_match.group(1))
            month = month_map[text_date_match.group(2)]
            try:
                res["date"] = f"2026-{month:02d}-{int(day_str):02d}"
            except ValueError:
                res["date"] = None

    # Lab mapping
    if "python lab 1" in req_lower or "python lab-1" in req_lower or re.search(r"\blab1\b", req_lower):
        res["lab"] = "LAB1"
    elif "python lab 2" in req_lower or "python lab-2" in req_lower or re.search(r"\blab2\b", req_lower):
        res["lab"] = "LAB2"
    elif "ai lab" in req_lower or "artificial intelligence" in req_lower or re.search(r"\blab3\b", req_lower):
        res["lab"] = "LAB3"
    elif "iot" in req_lower or "network" in req_lower or re.search(r"\blab4\b", req_lower):
        res["lab"] = "LAB4"
    elif "seminar hall" in req_lower or re.search(r"\blab5\b", req_lower):
        res["lab"] = "LAB5"
    elif "python lab" in req_lower:
        # Ambiguous: no number specified
        res["lab"] = None

    # Slot mapping
    if re.search(r"\b(fn|forenoon|morning|9:00|9:30|10:00|10:30|11:00|am)\b", req_lower):
        res["slot"] = "FN"
    elif re.search(r"\b(an|afternoon|evening|1:30|2:00|2:30|3:00|pm)\b", req_lower):
        res["slot"] = "AN"

    # Students count
    stud_match = re.search(r"(\d+)\s*(?:students?|participants?|members?|pax)?", req_lower)
    # Search explicitly for "for <number> students" or "<number> students"
    explicit_stud = re.search(r"\b(\d+)\s+students\b", req_lower)
    if explicit_stud:
        res["students"] = int(explicit_stud.group(1))
    elif stud_match:
        # Avoid picking the date day as student count
        candidates = re.findall(r"\b(\d+)\b", request_text)
        found_num = None
        for c in candidates:
            val = int(c)
            # if val is day number or year, skip unless followed by students
            if val == 2026 or (res["date"] and str(val) in res["date"].split("-")[1:]):
                continue
            if val > 5:
                found_num = val
                break
        res["students"] = found_num

    # Summary
    words = request_text.strip().split()
    res["summary"] = " ".join(words[:12])

    return res


def classify(request_text: str) -> Dict[str, Any]:
    """
    Classifies a request using LLM API.
    Retries once on invalid reply, then falls back to heuristic extractor.
    Copies ONLY the 5 requested fields.
    """
    system_prompt = get_system_prompt()
    raw_response = None
    parsed_json = None

    # Attempt 1
    raw_response = call_llm_api(system_prompt, request_text)
    if raw_response:
        try:
            # Clean possible markdown formatting
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw_response.strip())
            cleaned = re.sub(r"\s*```$", "", cleaned)
            parsed_json = json.loads(cleaned)
        except Exception:
            parsed_json = None

    # Retry once if first attempt failed or was invalid
    if not parsed_json and raw_response is not None:
        raw_response = call_llm_api(system_prompt, f"RETRY: Strictly valid JSON. Request: {request_text}")
        if raw_response:
            try:
                cleaned = re.sub(r"^```(?:json)?\s*", "", raw_response.strip())
                cleaned = re.sub(r"\s*```$", "", cleaned)
                parsed_json = json.loads(cleaned)
            except Exception:
                parsed_json = None

    # Fallback if LLM unavailable or reply invalid
    if not parsed_json:
        parsed_json = heuristic_fallback_parser(request_text)

    # Filter: Copy ONLY the allowed 5 fields
    safe_dict = {}
    for field in ALLOWED_FIELDS:
        safe_dict[field] = parsed_json.get(field, None)

    return safe_dict


# ==========================================
# 3. Python Verification & Status Cascade
# ==========================================

def check_date(date_str: Optional[str], request_text: str) -> Tuple[bool, Optional[datetime], str]:
    """
    Validates that:
      1. Date is a real calendar date (via datetime).
      2. Date is inside the semester.
      3. The day number appears in the request text.
    """
    if not date_str:
        return False, None, "Date is missing"

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return False, None, f"Invalid calendar date format: {date_str}"

    if not (SEMESTER_START <= dt <= SEMESTER_END):
        return False, None, f"Date {date_str} outside semester bounds"

    day_num = str(dt.day)
    # Check if day number appears as word boundary or ordinal (e.g. '15', '15th', '08')
    pattern = rf"\b0?{day_num}(?:st|nd|rd|th)?\b"
    if not re.search(pattern, request_text, re.IGNORECASE):
        return False, None, f"Day number {day_num} does not appear in request text"

    return True, dt, "Valid date"


def is_valid(parsed: Dict[str, Any], request_text: str) -> Tuple[bool, str]:
    """
    Fact checks student count and date presence against raw request text.
    """
    stud = parsed.get("students")
    if stud is not None:
        pattern = rf"\b{stud}\b"
        if not re.search(pattern, request_text):
            return False, f"Student count {stud} does not appear in request text"

    valid_d, _, reason_d = check_date(parsed.get("date"), request_text)
    if not valid_d and parsed.get("date") is not None:
        return False, reason_d

    return True, "Facts verified"


def decide(
    parsed: Dict[str, Any],
    raw_text: str,
    labs: Dict[str, Dict[str, Any]],
    confirmed_bookings: set,
    held_slots: set
) -> Tuple[str, str]:
    """
    Python decides the status in strict sequential order:
      1. Fact check (date validity, semester bounds, presence in text)
      2. needs_more_info: missing lab, date, slot, or students
      3. lab_closed: date is a Sunday
      4. over_capacity: students > lab capacity
      5. conflict: (date, slot, lab) taken in bookings.csv or earlier in this run
      6. available: holds slot for later requests
    """
    # 1. Fact checking
    fact_ok, fact_msg = is_valid(parsed, raw_text)
    if not fact_ok:
        return "needs_more_info", fact_msg

    lab = parsed.get("lab")
    date_str = parsed.get("date")
    slot = parsed.get("slot")
    students = parsed.get("students")

    # 2. Check for missing information
    if not lab or not date_str or not slot or students is None:
        missing = [k for k, v in [("lab", lab), ("date", date_str), ("slot", slot), ("students", students)] if v is None]
        return "needs_more_info", f"Missing required fields: {', '.join(missing)}"

    if lab not in labs:
        return "needs_more_info", f"Unrecognized lab code: {lab}"

    # 3. Lab closed on Sundays
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if dt.weekday() == 6:  # Sunday
            return "lab_closed", f"Lab closed on Sundays ({date_str} is a Sunday)"
    except ValueError:
        return "needs_more_info", "Invalid date"

    # 4. Over capacity
    capacity = labs[lab]["capacity"]
    if students > capacity:
        return "over_capacity", f"Requested {students} students exceeds {lab} capacity of {capacity}"

    # 5. Conflict checking (both bookings.csv and intra-run held slots)
    slot_key = (date_str, slot, lab)
    if slot_key in confirmed_bookings:
        return "conflict", f"Slot already booked in confirmed bookings ({date_str} {slot} {lab})"
    if slot_key in held_slots:
        return "conflict", f"Slot already taken by an earlier request in this run ({date_str} {slot} {lab})"

    # 6. Available
    held_slots.add(slot_key)
    return "available", "Slot available and tentatively held"


# ==========================================
# 4. Report Writing (Output Files)
# ==========================================

def write_reports(
    all_results: List[Dict[str, Any]],
    labs: Dict[str, Dict[str, Any]],
    output_dir: str = "."
) -> None:
    """Writes the four required output files according to specifications."""
    results_file = os.path.join(output_dir, "results.csv")
    schedule_file = os.path.join(output_dir, "schedule.csv")
    issues_file = os.path.join(output_dir, "issues.csv")
    summary_file = os.path.join(output_dir, "summary.txt")

    # 1. results.csv
    with open(results_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "sent", "lab", "date", "slot", "students", "status", "reason"])
        for item in all_results:
            writer.writerow([
                item["id"],
                item["sent"],
                item["parsed"].get("lab") or "",
                item["parsed"].get("date") or "",
                item["parsed"].get("slot") or "",
                item["parsed"].get("students") or "",
                item["status"],
                item["reason"]
            ])

    # 2. schedule.csv (available requests in chronological date, slot order)
    available_items = [item for item in all_results if item["status"] == "available"]
    available_items.sort(key=lambda x: (x["parsed"].get("date", ""), x["parsed"].get("slot", ""), x["parsed"].get("lab", "")))

    with open(schedule_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "date", "slot", "lab", "students", "summary"])
        for item in available_items:
            writer.writerow([
                item["id"],
                item["parsed"].get("date"),
                item["parsed"].get("slot"),
                item["parsed"].get("lab"),
                item["parsed"].get("students"),
                item["parsed"].get("summary")
            ])

    # 3. issues.csv (everything that cannot be booked as asked)
    issue_items = [item for item in all_results if item["status"] != "available"]
    with open(issues_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "sent", "status", "reason", "request"])
        for item in issue_items:
            writer.writerow([
                item["id"],
                item["sent"],
                item["status"],
                item["reason"],
                item["raw_request"]
            ])

    # 4. summary.txt (counts by status and by lab)
    status_counts = {}
    lab_counts = {lab: 0 for lab in labs}

    for item in all_results:
        s = item["status"]
        status_counts[s] = status_counts.get(s, 0) + 1
        lab = item["parsed"].get("lab")
        if lab and lab in lab_counts:
            lab_counts[lab] += 1

    with open(summary_file, mode="w", encoding="utf-8") as f:
        f.write("=" * 45 + "\n")
        f.write("LAB BOOKING REQUEST SORTER - SUMMARY REPORT\n")
        f.write("=" * 45 + "\n\n")
        f.write(f"Total Requests Processed: {len(all_results)}\n")
        f.write(f"Successfully Scheduled:   {len(available_items)}\n")
        f.write(f"Flagged Issues:           {len(issue_items)}\n\n")

        f.write("-" * 30 + "\n")
        f.write("REQUEST COUNTS BY STATUS\n")
        f.write("-" * 30 + "\n")
        for status in ["available", "needs_more_info", "lab_closed", "over_capacity", "conflict"]:
            f.write(f"{status.ljust(18)} : {status_counts.get(status, 0)}\n")

        f.write("\n" + "-" * 30 + "\n")
        f.write("REQUEST COUNTS BY LAB\n")
        f.write("-" * 30 + "\n")
        for lab_code, lab_info in labs.items():
            f.write(f"{lab_code} ({lab_info['name']}) : {lab_counts.get(lab_code, 0)}\n")
        f.write("=" * 45 + "\n")


# ==========================================
# 5. Main Execution Flow
# ==========================================

def run_sorter(data_dir: str = "."):
    labs_file = os.path.join(data_dir, "labs.csv")
    bookings_file = os.path.join(data_dir, "bookings.csv")
    requests_file = os.path.join(data_dir, "requests.csv")

    print("[*] Starting Lab Booking Request Sorter...")
    labs = load_labs(labs_file)
    print(f"[*] Loaded {len(labs)} labs.")
    confirmed_bookings = load_bookings(bookings_file)
    print(f"[*] Loaded {len(confirmed_bookings)} pre-confirmed bookings.")
    requests = load_requests(requests_file)
    print(f"[*] Loaded {len(requests)} requests to process.\n")

    held_slots = set()
    all_results = []

    for req in requests:
        req_id = req["id"]
        sent_date = req["sent"]
        raw_text = req["request"]

        # Classify via LLM (or fallback)
        parsed = classify(raw_text)

        # Decide status via Python business logic
        status, reason = decide(parsed, raw_text, labs, confirmed_bookings, held_slots)

        all_results.append({
            "id": req_id,
            "sent": sent_date,
            "raw_request": raw_text,
            "parsed": parsed,
            "status": status,
            "reason": reason
        })
        print(f"[{req_id}] -> {status.upper()} | {parsed.get('lab')} | {parsed.get('date')} | {reason}")

    print("\n[*] Writing output files...")
    write_reports(all_results, labs, output_dir=data_dir)
    print("[+] Done! Generated results.csv, schedule.csv, issues.csv, summary.txt")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    run_sorter(base_dir)
