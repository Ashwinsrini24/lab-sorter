# AI Decision Journal & 400-Word Reflection

**Programme:** CIT AI-Native Engineering Programme · Semester 1 · Assessment 5  

---

## Part 1: AI Decision Journal

| Stage | Decision Faced | Options Considered | Decision Made & Rationale |
| :--- | :--- | :--- | :--- |
| **Architecture** | Where should status decisions (`available`, `conflict`, `over_capacity`) happen? | 1. Let the LLM output the status directly in JSON.<br>2. Restrict LLM to entity extraction; evaluate status rules entirely in Python. | **Option 2:** LLMs are prone to hallucinating dates, missing capacity limits, and cannot reliably cross-reference earlier requests without complex context injection. Python provides 100% deterministic, verifiable rule enforcement. |
| **Date Parsing** | How should relative dates like "tomorrow" or "next Friday" be treated? | 1. Have Python calculate the relative offset from `sent` date.<br>2. Strictly set `date: null` and flag `needs_more_info`. | **Option 2:** The project spec states only calendar dates explicitly written in the request are valid. Guessing relative dates without confirmed student/faculty alignment risks catastrophic slot misallocations. |
| **API Failure Handling** | What happens if the LLM API quota is exceeded, offline, or returns invalid syntax? | 1. Crash or raise uncaught exception.<br>2. Retry once, then gracefully fall back to a deterministic regex/heuristic parser. | **Option 2:** Retrying once catches transient formatting anomalies. The heuristic fallback guarantees business continuity and zero downtime even without an active internet connection. |
| **State Tracking** | How to handle conflicts between two new requests within the same incoming batch? | 1. Only check against `bookings.csv`.<br>2. Maintain an in-memory `held_slots` set that reserves slots immediately when granted. | **Option 2:** Only checking `bookings.csv` causes race conditions where two simultaneous requests for the same room both get marked `available`. In-memory reservation flags the second as `conflict`. |

---

## Part 2: 400-Word Reflection

Building the Lab Booking Request Sorter provided a deep, practical understanding of designing robust AI-native architectures within real-world constraints. Early in the project, the primary temptation was to treat the Large Language Model as an end-to-end reasoning engine capable of taking a text request, reading the lab register, and outputting the final booking decision. However, testing rapidly exposed the critical flaw in this approach: LLMs are probabilistic text generators, not deterministic state machines. Asking an LLM to reliably compare room capacities, compute chronological clashing across dozens of requests, and check day-of-the-week constraints leads to subtle hallucinations, arithmetic slip-ups, and undetected scheduling conflicts.

This revelation cemented the central design paradigm of this project: strict separation of concerns. We constrained the LLM to a single, focused job—extracting unstructured natural language entities into a well-defined 5-key JSON schema using the 5-role prompt framework (Authority, Exemplar, Constraint, Rubric, Metadata). By stripping the LLM of decision-making authority, the system eliminated prompt injection vulnerabilities, such as requests claiming "urgent faculty override." 

All scheduling rules, fact validations, and conflict decisions were implemented in pure, transparent Python code. Utilizing Python's `datetime` module allowed us to rigorously verify calendar validity, check semester boundaries, and flag Sunday closures with mathematical certainty. Furthermore, verifying that extracted numbers and dates explicitly appear in the raw request text established an impenetrable defense against hallucinations.

Equally transformative was implementing the Judgment Framework and human checkpoint. In automated scheduling, the cost of an erroneous booking can disrupt an entire department. Therefore, designing the tool so that it produces tentative schedules without ever writing directly to `bookings.csv` proved that responsible AI engineering is not about automating humans out of the loop, but about empowering them. The lab in-charge remains the sole authority, armed with an organized, clash-free tentative schedule and a transparent log of rejected issues.

Ultimately, this project demonstrated that the most effective AI-native systems do not rely on AI everywhere. Instead, they pair the linguistic flexibility of modern language models with the unflinching rigor of deterministic software engineering.
