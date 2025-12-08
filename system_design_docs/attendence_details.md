BIG PICTURE (ONE-LINE SUMMARY)

Your system records every punch (check-in, breaks, check-out), applies company policy + shift rules, checks for holidays & approved leave, and then automatically decides:

✅ Present / Half-day / Short-hours / Absent

✅ Late minutes

✅ Early leaving

✅ Overtime

✅ Night shift

✅ Holiday / Weekend

✅ All this directly powers payroll ✅

✅ 1️⃣ WHAT STARTS ATTENDANCE CALCULATION?

Whenever any of these happens:

Employee checks in

Employee checks out

Employee starts break

Employee ends break

OR HR manually updates attendance

👉 Your system automatically recalculates attendance for that date.

This function is called:

AttendanceService.recalculate_for_date(employee_id, date)


You can think of this as:

✅ “Recalculate this person’s full attendance for today from scratch.”

✅ 2️⃣ WHICH POLICY IS APPLIED?

Your system has a dynamic attendance policy table called:

attendance_policies


It contains rules like:

Late grace minutes

Early exit grace

Full-day required %

Half-day required %

Overtime enabled or not

✅ For each day, system:

Picks the latest policy that existed on that day

If none exists → uses safe default rules

So policy can change over time and old attendance stays correct ✅

✅ 3️⃣ DOES SYSTEM CHECK FOR HOLIDAYS, WEEKENDS & LEAVE?

Yes. Before deciding status, it checks:

Check	From Table	Meaning
Weekend	System date logic	Saturday/Sunday
Holiday	holidays	Company holiday
Approved Leave	leave_requests	HR-approved leave

So system knows if that employee:

Was on leave ✅

Had a holiday ✅

It was a weekend ✅

✅ 4️⃣ HOW DOES SYSTEM FIND SHIFT DETAILS?

It looks into:

employee_shifts  +  shifts


It finds:

Which shift the employee is assigned

Start time

End time

Whether it's a night shift

✅ Shift is chosen only if:

Shift effective date matches today

If no shift is assigned → system assumes:

Default 8-hour shift for that day

✅ 5️⃣ HOW DOES SYSTEM READ DAILY WORK TIME?

Next, your system loads raw punch events from:

attendance_events


These include:

Check-in

Break-start

Break-end

Check-out

It then calculates:

✅ Actual worked time
✅ Break time
✅ First check-in time
✅ Last checkout time

This gives:

Metric	Meaning
total_hours	Full time between check-in and check-out
net_hours	Actual working time minus breaks
break_minutes	Total break time
check_in	First punch
check_out	Last punch
✅ 6️⃣ HOW LATE MINUTES ARE CALCULATED

If employee is assigned a shift:

Rule
Late = Actual Check-in – Shift Start
If late > Grace minutes → Mark Late

✅ Example:

Shift starts: 9:00 AM

Grace: 10 mins

Employee checks in: 9:20

Late = 20 mins → Employee is marked late

✅ 7️⃣ HOW EARLY EXIT IS CALCULATED

If employee leaves before shift ends:

Rule
Shift End – Actual Checkout
If > Early Grace → Mark Early Exit

✅ Example:

Shift ends: 6:00 PM

Grace: 10 mins

Checkout: 5:30 PM

Early exit = 30 mins → Early exit marked

✅ 8️⃣ HOW OVERTIME IS CALCULATED

Overtime is calculated if:

Overtime is enabled in policy

Net working hours > Required shift hours

✅ Example:

Shift: 8 hours

Worked: 10 hours

Overtime = 2 hours (120 minutes)

✅ 9️⃣ HOW FINAL DAILY STATUS IS DECIDED

Based on actual working vs required shift hours:

Condition	Status
≥ 75% of shift	✅ Present
≥ 50% but < 75%	✅ Half-day
< 50%	✅ Short-hours
No punches + no leave	❌ Absent
Approved leave	✅ On-leave
Holiday	✅ Holiday
Weekend	✅ Week-off
✅ 10️⃣ WHAT IF EMPLOYEE DOES NOT PUNCH AT ALL?

System automatically assigns:

Situation	Status
Holiday	Holiday
Approved leave	On-leave
Weekend	Week-off
Otherwise	Absent

✅ Even without a single punch, attendance is finalized correctly.

✅ 11️⃣ FINAL DATA STORED IN ATTENDANCE TABLE

After all calculation, system saves:

Field	Purpose
check_in	First punch
check_out	Last punch
net_hours	Actual work
late_minutes	Late
early_exit_minutes	Early
overtime_minutes	Extra work
is_weekend	Sat/Sun
is_holiday	Holiday
is_night_shift	Night
status	present / half day / absent
is_payroll_locked	Salary freeze
locked_at	Lock timestamp

✅ This single row per day is what payroll reads.

✅ 12️⃣ HOW PAYROLL USES THIS

Your payroll engine uses only:

attendance status

late minutes

early exit

overtime minutes

net hours

night shift

holidays

It never directly uses leave balance ✅
Only whether the day became absent or on-leave.