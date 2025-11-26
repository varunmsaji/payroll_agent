from fastapi import FastAPI
from app.api.dashboard_api import router as dashboard_router
from app.api.employee_detail import router as employee_detail_router
from app.api.attendence_dashboard import router as attendence_dashboard_router
from fastapi.middleware.cors import CORSMiddleware
from app.api.shifts import router as shifts_router
from app.api.leave_api import router as leave_router

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Allow all frontends (React, mobile, etc.)
    allow_credentials=True,
    allow_methods=["*"],        # GET, POST, PUT, DELETE
    allow_headers=["*"],        # Authorization, Content-Type, etc.
)

app.include_router(dashboard_router)
app.include_router(employee_detail_router)
app.include_router(shifts_router)
app.include_router(attendence_dashboard_router)
app.include_router(leave_router)