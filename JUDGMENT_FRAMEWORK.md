# Component 5: Judgment Framework

This framework documents the AI-safety, accountability, and decision boundaries of the **Lab Booking Request Sorter**.

## Judgment Framework Matrix

| Tool Component | 1. Cost of Being Wrong | 2. Can it be Verified Without AI? | 3. Who is Accountable? |
| :--- | :--- | :--- | :--- |
| **LLM Entity Extraction** (`lab`, `date`, `slot`, `students`, `summary`) | **Moderate to Low:** If the LLM extracts an incorrect date or count, downstream deterministic validation checks facts against raw text. Worst case: request is routed to `needs_more_info`. | **Yes:** A simple regex or string search against the original request text confirms whether extracted day and numbers actually appear. | **Software Engineer / Pipeline Developer** (responsible for prompt design, constraints, and fallback logic). |
| **Fact-Checking & Date Logic** (`check_date`, `is_valid`) | **High:** If an invalid calendar date or out-of-semester date slipped through, scheduling could break or schedule non-existent slots. | **Yes:** Standard Python library `datetime` and mathematical calendar rules deterministically verify calendar validity. | **Software Engineer** (responsible for robust date parsing and boundary definitions). |
| **Capacity & Sunday Checks** (`lab_closed`, `over_capacity`) | **High:** Double bookings or overcrowding violates safety regulations; Sunday bookings require campus staff that are not present. | **Yes:** Verified completely via simple lookup against `labs.csv` and `weekday() == 6`. No AI involved. | **Software Engineer** (responsible for rule execution order). |
| **Clash & Conflict Detection** (`conflict`, `held_slots`) | **Critical:** Scheduling two batches into the same room creates direct room conflicts during live classes. | **Yes:** Pure deterministic set comparison against `bookings.csv` and in-memory session state. | **Software Engineer** (responsible for maintaining accurate state and chronological ordering). |
| **Final Confirmation & Commitment** (Writing to master schedule) | **Catastrophic if Automated:** An automated system committing bookings directly could lock out faculty without recourse if an edge case is mishandled. | **Yes:** Human administrator checks tentative `schedule.csv` against institutional priorities. | **Human Checkpoint: The Lab In-Charge.** The tool NEVER writes to `bookings.csv`. The lab in-charge reviews tentative output and officially signs off on bookings. |

---

## The Human Checkpoint: Lab In-Charge

The overarching safety principle of this system is **zero automated authority**:
1. **Tentative by Design:** The output `schedule.csv` is explicitly marked as tentative proposals.
2. **Read-Only Access:** The system has read-only access to `bookings.csv`. It possesses no writing routine targeting confirmed registers.
3. **Accountability Anchor:** The lab in-charge remains the sole authoritative actor who issues keys, updates the physical register, and commits records to `bookings.csv`.
