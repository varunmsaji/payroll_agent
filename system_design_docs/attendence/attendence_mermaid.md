┌──────────────────────────┐
│ Start: Recalculate day   │
│  (employee + date)       │
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│ Load Attendance Policy   │
│ (late rules, overtime…)  │
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│ Check if payroll locked  │
│  → STOP if locked        │
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│ Check: weekend? holiday? │
│ approved leave?          │
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│ Get employee shift       │
│ (start, end, night?)     │
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────┐
│ Fetch attendance events  │
│ (check-ins, breaks...)   │
└──────────────┬───────────┘
               │
         ┌─────┴──────┐
         │            │
         ▼            ▼
  NO EVENTS     EVENTS FOUND
         │            │
         ▼            ▼
┌────────────────┐   ┌──────────────────────────┐
│ Mark status as │   │ Compute:                │
│ absent/leave/  │   │  • work time            │
│ holiday/weekoff│   │  • break time           │
└───────┬────────┘   │  • check-in/out         │
        │            └───────────┬────────────┘
        │                        │
        │                        ▼
        │               ┌─────────────────────┐
        │               │ Check late + early │
        │               │ exit               │
        │               └─────────┬──────────┘
        │                         │
        │                         ▼
        │               ┌─────────────────────┐
        │               │ Compute overtime   │
        │               │ (no late recovery) │
        │               └─────────┬──────────┘
        │                         │
        │                         ▼
        │               ┌─────────────────────┐
        │               │ Decide final status │
        │               │ present/half/short │
        │               └─────────┬──────────┘
        │                         │
        ▼                         ▼
┌──────────────────────────┐
│ Save final record in     │
│ attendance table         │
└──────────────┬───────────┘
               │
               ▼
        ┌───────────────┐
        │     DONE      │
        └───────────────┘
