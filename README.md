# Lab Booking Request Sorter

**Programme:** CIT AI-Native Engineering Programme · Semester 1 · Assessment 5  
**Domain:** Scheduling  
**Weightage:** 40% (Week 15 Capstone Showcase)  

---

## 📌 Project Overview
The **Lab Booking Request Sorter** is a console-based Python tool designed to streamline computer lab allocations in academic departments. It ingests unstructured, informal natural-language booking requests from faculty and student leads, extracts key entities using an LLM guided by a 5-role prompt, verifies facts using Python's standard `datetime` library, and applies institutional scheduling policies to produce a tentative schedule and flagged issue reports.

**Core Philosophy:** The tool **never confirms or writes bookings** to the official register (`bookings.csv`). All final bookings are authorized by the **lab in-charge (Human Checkpoint)**.

---

## 📁 Repository Structure
```
lab-sorter/
├── SPECIFICATION.md          # One-page signed-off specification (Component 1)
├── labs.csv                  # Lab definitions & seating capacities
├── bookings.csv              # Master register of confirmed bookings (Read-Only)
├── requests.csv              # 22 realistic booking requests (Chronological order)
├── system_prompt.txt         # 5-role framework system prompt (Component 3)
├── lab_sorter.py             # Main Python program (Component 2)
├── test_eval_harness.py      # Eval harness & 3 red-team attack tests (Component 4)
├── JUDGMENT_FRAMEWORK.md     # Risk, verification & accountability matrix (Component 5)
├── COST_AND_LATENCY.md       # API call latency and daily cost model (Component 6)
├── REFLECTION.md             # AI Decision Journal & 400-word reflection
├── .gitignore                # Protects API keys and environment files (Component 7)
├── results.csv               # Generated: All requests with status and explanation
├── schedule.csv              # Generated: Tentative confirmed schedule sorted by date
├── issues.csv                # Generated: Flagged requests that could not be booked
└── summary.txt               # Generated: Aggregate request statistics
```

---

## 🚀 How to Run & Test (Step-by-Step Instructions)

### 1. Prerequisites
- Python 3.8+ (Uses standard library: `csv`, `json`, `datetime`, `re`, `urllib`).
- No external pip dependencies required.

### 2. (Optional) Set LLM API Key
The system includes an automatic offline heuristic fallback. To run with a live cloud LLM API, set your API key as an environment variable (the key is **never** written in code):

**Windows PowerShell:**
```powershell
$env:GEMINI_API_KEY="your-api-key-here"
# or
$env:GROQ_API_KEY="your-api-key-here"
```

**Linux / macOS:**
```bash
export GEMINI_API_KEY="your-api-key-here"
```

*(If no key is set, the tool automatically uses its built-in fallback parser with 100% fidelity to the specification rules).*

---

### 3. Run the Sorter Pipeline (End-to-End)
Execute the main program from the project directory:
```powershell
python lab_sorter.py
```
**Expected Output:**
- The console will display each request ID, status, lab, date, and reason.
- Four output files are automatically generated or updated:
  1. `results.csv`
  2. `schedule.csv`
  3. `issues.csv`
  4. `summary.txt`

---

### 4. Run the Evaluation Harness & Red-Team Tests
Execute the automated test suite:
```powershell
python test_eval_harness.py
```
**Expected Output:**
- **Part 1 (Eval Harness):** 5 test requests, validating each of the 5 statuses (`available`, `needs_more_info`, `lab_closed`, `over_capacity`, `conflict`). Score: **5/5 passed (100%)**.
- **Part 2 (Red-Team Attacks):** 3 adversarial inputs:
  1. Relative date attack ("next Monday") $\rightarrow$ caught as `needs_more_info`.
  2. Impossible calendar date attack ("31 November") $\rightarrow$ caught as `needs_more_info`.
  3. Prompt injection & false urgency $\rightarrow$ prompt overrides rejected, caught as `needs_more_info`.

---

## 🛡️ Status Evaluation Cascade Order
Python decides status strictly in this sequence:
1. **Fact Checking:** Verified date format, semester bounds (Oct 1 – Dec 31, 2026), and presence of day number and student count in original text.
2. `needs_more_info`: Any required field missing (`lab`, `date`, `slot`, `students`).
3. `lab_closed`: Requested date falls on a Sunday.
4. `over_capacity`: Number of students exceeds the lab's capacity.
5. `conflict`: Lab and slot already reserved in `bookings.csv` OR held by an earlier request in this run.
6. `available`: Tentatively held for the lab in-charge to confirm.

---

## 📋 Academic Submission Checklist
- [x] GitHub repo structure with `.gitignore` protecting secrets
- [x] One-page specification (`SPECIFICATION.md`)
- [x] System prompt text file (`system_prompt.txt`)
- [x] Modular Python program (`lab_sorter.py`)
- [x] Eval harness and red-team tests (`test_eval_harness.py`)
- [x] Judgment Framework table (`JUDGMENT_FRAMEWORK.md`)
- [x] Cost and latency note (`COST_AND_LATENCY.md`)
- [x] AI Decision Journal & 400-word reflection (`REFLECTION.md`)
- [x] All 3 input CSV files and 4 generated output files
