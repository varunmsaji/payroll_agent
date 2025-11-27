# app/api/workflow_router.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from app.database import workflow_database as workflow_db

router = APIRouter(prefix="/workflow", tags=["Workflow Engine"])


# ================================
# ✅ SCHEMAS
# ================================
class Step(BaseModel):
    step_order: int
    role: str
    is_final: bool


class WorkflowCreate(BaseModel):
    name: str
    module: str
    steps: List[Step]


class StartWorkflow(BaseModel):
    approver_id: int


class Action(BaseModel):
    remarks: str = ""


# ================================
# ✅ ROUTES
# ================================
@router.post("/create")
def create_workflow(req: WorkflowCreate):
    wf_id = workflow_db.create_workflow(
        req.name, req.module, [s.dict() for s in req.steps]
    )
    return {"message": "Workflow created", "workflow_id": wf_id}


@router.post("/{module}/start/{request_id}")
def start_workflow(module: str, request_id: int, req: StartWorkflow):
    wf = workflow_db.get_active_workflow(module)
    workflow_db.start_workflow(module, request_id, wf["id"], req.approver_id)
    return {"message": "Workflow Started"}


@router.post("/{module}/{request_id}/approve")
def approve(module: str, request_id: int, req: Action):
    result = workflow_db.approve_step(module, request_id, req.remarks)
    return {
        "message": "Step Approved",
        "next_step": result
    }



@router.post("/{module}/{request_id}/reject")
def reject(module: str, request_id: int, req: Action):
    workflow_db.reject_step(module, request_id, req.remarks)
    return {"message": "Rejected"}


@router.get("/{module}/{request_id}")
def get_status(module: str, request_id: int):
    return workflow_db.get_workflow_status(module, request_id)
