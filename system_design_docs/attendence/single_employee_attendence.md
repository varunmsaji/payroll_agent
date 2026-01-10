Great — let’s walk through ONE employee step-by-step like a real workday, with real timestamps — and I’ll explain exactly what the code does at every moment.

We’ll use this scenario:

Thing	Value
Employee shift	9:00 AM – 5:00 PM (8 hours)
Check-in	09:00
Break	1–1:30 PM
Check-out	05:10 PM
Policy	10-minute grace, overtime allowed
👨‍💼 Employee Timeline (Mock Day)
⏰ 09:00 — Employee Checks In

Employee hits:

POST /check-in


Code called:

AttendanceService.check_in()

What happens internally

1️⃣ Code ensures he doesn't already have an open check-in

_ensure_no_open_checkin()


2️⃣ It records an event in attendance_events:

event_type	time
check_in	09:00

3️⃣ Then it calls:

recalculate_for_date(employee_id, today)


So the system immediately updates his attendance summary.

🔍 Recalculate begins (this function runs ALL logic)
AttendanceService.recalculate_for_date()

Step 1 — Load Attendance Policy from DB

Reads attendance_policies

Late grace = 10 minutes
Overtime allowed
Full day = 75% of shift

If DB fails — uses defaults.

Step 2 — Ensure not locked for payroll

Looks at attendance table:

is_payroll_locked?


If locked → STOP
(Not locked now → continue 🎯)

Step 3 — Check day type

Database checks:

holidays → not holiday

leave_requests → no approved leave

weekend? → no (weekday)

Step 4 — Load Shift

From shifts / employee_shifts

start = 09:00
end = 17:00
required_hours = 8.0

Step 5 — Load Events For The Day

From attendance_events

Only one event exists now:

type	time
check_in	09:00
Step 6 — Compute Work & Breaks

Function:

_compute_work_and_breaks()


Finds:

check-in = 09:00

check-out = None (hasn't checked out yet)

net_hours = 0 (so far)

break_minutes = 0

So system stores:

status = short_hours


…and saves a partial day row in attendance.

The row keeps updating throughout the day — not final yet.

☕ 1:00 PM — Break Starts

Employee calls:

POST /break/start


System logs:

type	time
break_start	13:00

Recalculate runs again.

Work calculated now:

09:00 → 13:00 = 4 hours worked


Break counter starts ticking.

🍽 1:30 PM — Break Ends

Call:

POST /break/end


Event logged:

type	time
break_end	13:30

Recalculate:

total work (so far):
4h before break

break total:
30 minutes

now active working session reopened

Attendance snapshot updated.

🕔 5:10 PM — Check Out

Employee calls:

POST /check-out


Event logged:

type	time
check_out	17:10

Now final recalculation happens.

📊 FINAL CALCULATION (Important Part)
1️⃣ Work and Breaks
09:00–13:00 = 4.0h
13:30–17:10 = 3.67h
--------------------------------
Total work = 7.67h (≈ 7h 40m)

Break = 30m

2️⃣ Total span in office
09:00–17:10 = 8h 10m

3️⃣ Late calculation

Shift start: 09:00
Check-in: 09:00

Late = 0 minutes

4️⃣ Early exit check

Shift end: 17:00
Check-out: 17:10

Left late, not early

5️⃣ Overtime

Shift end: 17:00
Actual checkout: 17:10

Overtime:

10 minutes


Code also ensures:

❌ late time cannot convert into overtime
✔ only time AFTER shift counts

6️⃣ Decide Status

Required hours = 8.0
Full-day threshold = 75%

Full day threshold:

8 × 0.75 = 6 hours


Employee worked 7.67 hours, so:

status = present

✔️ Final Attendance Row Saved

Table: attendance

Field	Value
check_in	09:00
check_out	17:10
net_hours	7.67
total_hours	8.10
break_minutes	30
late_minutes	0
overtime_minutes	10
is_late	False
is_overtime	True
status	present
🎯 What To Remember (Beginner Summary)
Every time employee does something:

✔ system logs event
✔ recomputes the whole day
✔ saves final summary

Tables role:

📜 attendance_events → raw history (like CCTV)
📊 attendance → final truth (used by payroll)