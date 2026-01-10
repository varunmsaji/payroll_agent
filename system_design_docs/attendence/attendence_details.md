present / half_day / short_hours / leave / holiday / weekend
8️⃣ Save result to attendance table.

🚀 Now Let’s Walk Through the Code Step-By-Step
We will focus on:

scss
Copy code
recalculate_for_date()
because every attendance calculation ends there.

⭐ Step 1 — Load Attendance Policy (from DB)
python
Copy code
policy = AttendancePolicyDB.get_policy_for_date(dt)
This checks the table:

nginx
Copy code
attendance_policies
and loads rules like:

late grace minutes

early exit grace

full-day fraction

overtime on/off

If nothing exists → default values are used.

➡️ This lets HR change policy anytime — AND supports history.

⭐ Step 2 — Check If Attendance Is Locked
python
Copy code
existing = AttendanceDB.get_by_employee_and_date(employee_id, dt)
if existing and existing.get("is_payroll_locked"):
    raise ValueError("Attendance locked for payroll.")
Meaning:

If payroll already processed this day → DON'T touch it.

⭐ Step 3 — Identify Day Type
python
Copy code
is_weekend = dt.weekday() >= 5
is_holiday = HolidayDB.is_holiday(dt)
has_leave = LeaveDB.has_approved_leave(employee_id, dt)
Database tables involved:

Table	Used For
holidays	Is today holiday?
leave_requests	Does employee have approved leave?

⭐ Step 4 — Get Employee Shift
python
Copy code
shift = ShiftDB.get_employee_shift(employee_id, dt)
window_start, window_end, required_hours, is_night_shift, shift_id = cls._get_shift_window(shift, dt)
employee_shifts / shifts tables are used.

This decides:

when shift starts/ends

if shift crosses midnight

expected working hours

Example:

Start	End	Night?	Required hours
9:00	18:00	❌	9 hrs
22:00	06:00	✅	8 hrs

⭐ Step 5 — Load All Attendance Events (from logs)
python
Copy code
events = AttendanceEventDB.get_events_for_window(employee_id, window_start, window_end)
This reads from:

nginx
Copy code
attendance_events
Examples stored:

event_type	time
check_in	09:05
break_start	13:00
break_end	13:30
check_out	18:10

Think of this as the FULL history / audit log.

⭐ Step 6 — If No Events (Absent / Leave / Holiday)
python
Copy code
if not events:
    return cls._handle_no_events(...)
Logic:

holiday → holiday

leave → on_leave

weekend → week_off

otherwise → absent

and still store it in attendance table.

⭐ Step 7 — Calculate Work and Break Time
python
Copy code
work_sec, break_sec, check_in, check_out = cls._compute_work_and_breaks(events)
This method:

1️⃣ Tracks working session durations
2️⃣ Tracks breaks
3️⃣ Determines first check-in and last check-out

Example:

kotlin
Copy code
09:00 → check in
13:00 → break start
13:30 → break end
18:00 → check out
Work =
(9–13) + (13:30–18) = 8.5 hr

Break =
(13–13:30) = 30 min

⭐ Step 8 — Calculate Late Arrival
python
Copy code
late_minutes, is_late = cls._compute_late(shift, dt, check_in)
Compares:

powershell
Copy code
actual check-in vs shift start
But ignores small delays (grace time).

⭐ Step 9 — Early Checkout
python
Copy code
early_exit_minutes, is_early = cls._compute_early_checkout(...)
Same concept — checks if they left early.

⭐ Step 10 — Calculate Overtime (Important!)
python
Copy code
overtime_minutes, is_overtime = cls._compute_overtime(...)
Rules:

✔ Only counts AFTER shift end
✔ Does NOT allow recovering late as overtime
✔ Can be disabled by policy

Very realistic HR behaviour.

⭐ Step 11 — Decide Status
python
Copy code
status = cls._decide_status(
    net_hours, required_hours, is_weekend, is_holiday, has_leave
)
Uses fractions from policy:

Full day if worked ≥ 75%

Half-day if worked ≥ 50%

Otherwise → short_hours

⭐ Step 12 — Save Final Record
Everything is merged into a single row and saved:

python
Copy code
return AttendanceDB.upsert_full_attendance(data)
Stored in:

nginx
Copy code
attendance
This table represents the final truth used by payroll.

🎯 Summary (Beginner Version)
Think of it like:

📜 Logs table = raw actions (audit history)
📊 Attendance table = final summary (one row per day)

Every time something happens (check-in/out), system:

✔ reloads policy
✔ fetches logs
✔ calculates hours
✔ updates final attendance

