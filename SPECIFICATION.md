# Capstone Project Specification: Lab Booking Request Sorter

**Programme:** CIT AI-Native Engineering Programme · Semester 1 · Assessment 5  
**Author:** Student Submission  
**Domain:** Scheduling  

---

## 1. What the Tool Does
The **Lab Booking Request Sorter** is a console-based Python tool that processes informal, unstructured, free-text lab booking requests submitted by faculty and student clubs (e.g., *"Book LAB1 on 15 Oct AN for 30 students"*). 

The tool uses a Large Language Model (LLM) strictly as an information extractor to extract entity details (`lab`, `date`, `slot`, `students`, `summary`) into structured JSON. Then, a deterministic Python business-logic engine validates facts, applies institutional scheduling constraints, detects clashes, and categorizes each request into one of five statuses. 

**Critical Boundary:** The tool **never confirms or commits bookings** to the master schedule (`bookings.csv`). It outputs tentative reports for the human lab in-charge, who retains final confirmation authority.

---

## 2. Input Specifications

The program reads three CSV files from the working directory:
1. `labs.csv`: Master register of available labs and capacities.
   - Header: `code,name,capacity`
   - Example: `LAB1,Python Lab 1,60`
2. `bookings.csv`: Pre-confirmed bookings established prior to tool execution.
   - Header: `date,slot,lab,booked_for`
   - Example: `2026-10-16,AN,LAB3,AI105 practical`
3. `requests.csv`: At least 20 raw booking requests in chronological order of arrival.
   - Header: `id,sent,request`
   - Example: `Q01,2026-10-08,"Need Python Lab 1 on 15 October afternoon for 55 students for CS101 practice"`

---

## 3. JSON Output Schema & Rules (LLM Extraction)

The LLM is strictly constrained to output JSON conforming to:
```json
{
  "lab": "LAB1",
  "date": "YYYY-MM-DD",
  "slot": "FN",
  "students": 45,
  "summary": "Short 12-word description"
}
```

### Extraction Field Rules
| Field | Allowed Values | Rule |
| :--- | :--- | :--- |
| `lab` | Standard lab code (`LAB1`, `LAB3`, etc.) or `null` | Must resolve to a known code. If ambiguous (e.g. "Python lab" with no number), return `null`. |
| `date` | `YYYY-MM-DD` or `null` | Only explicit calendar dates mentioned in the request. Relative dates (e.g. "tomorrow", "next Friday") must be returned as `null`. |
| `slot` | `FN`, `AN`, or `null` | `FN` for 9:00–12:30 or morning; `AN` for 1:30–4:30 or afternoon. Exact clock times map to these windows. Otherwise `null`. |
| `students`| Integer or `null` | Whole number explicitly mentioned in the request. If missing, return `null`. |
| `summary` | String | 12 words or fewer summarizing the booking purpose. Never claims priority or approval. |

---

## 4. Status Decision Pipeline (Strict Order of Execution)

Python evaluates extracted data in this deterministic sequence:

1. **Fact Checking (`is_valid()`, `check_date()`):**
   - **Date verification:** Date must be valid according to Python's `datetime` module.
   - **Semester bounds:** Date must lie inside the active semester (Semester 1: October 1, 2026 to December 31, 2026).
   - **Day number presence:** The day number (e.g., "15" or "15th") must explicitly appear in the raw request text.
   - **Student count presence:** The extracted student count integer must explicitly appear in the raw request text.
   - If any fact check fails, the field is invalidated / treated as missing.

2. **`needs_more_info`:**
   - Triggered if any mandatory field (`lab`, `date`, `slot`, or `students`) is `null` or missing.

3. **`lab_closed`:**
   - Triggered if the valid booking date falls on a Sunday (`datetime.weekday() == 6`).

4. **`over_capacity`:**
   - Triggered if `students` exceeds the capacity defined for that lab in `labs.csv`.

5. **`conflict`:**
   - Triggered if the `(date, slot, lab)` is already taken in `bookings.csv`, **OR** if it has already been claimed by an earlier request in the current run.

6. **`available`:**
   - Granted if none of the above conditions apply.
   - **Hold slot:** Once marked `available`, this `(date, slot, lab)` is added to the in-memory reserved set so subsequent conflicting requests are flagged.

---

## 5. Edge Cases Handled

1. **Relative Dates:** Requests saying "tomorrow" or "next Monday" cannot be safely mapped to a specific calendar date without ambiguity; extracted as `null` -> classified as `needs_more_info`.
2. **Ambiguous Lab Names:** Specifying "Computer Lab" when multiple exist returns `null` -> `needs_more_info`.
3. **Invalid Calendar Dates:** Dates such as "30 February" or "31 November" fail Python `datetime` parsing -> `needs_more_info`.
4. **Intra-run Clashes:** Two requests in `requests.csv` requesting the same lab and slot. The first valid request gets `available`, the second immediately receives `conflict`.
5. **LLM Hallucinations:** Any fields returned outside the requested 5 keys are discarded. If the LLM generates non-JSON or fails schema validation, the system retries once; if it fails again, fallback logic safely marks it `needs_more_info`.
6. **Sunday Requests:** Even if capacity and slot are free, college rules prohibit Sunday bookings -> `lab_closed`.

---

## 6. Output Files

- `results.csv`: Contains all requests with `id,sent,lab,date,slot,students,status,reason`.
- `schedule.csv`: Tentative schedule containing only `available` requests sorted chronologically by `date,slot,lab`.
- `issues.csv`: Contains all rejected requests (`needs_more_info`, `lab_closed`, `over_capacity`, `conflict`) alongside the original request text.
- `summary.txt`: Human-readable summary providing total count breakdown by status and by lab.
