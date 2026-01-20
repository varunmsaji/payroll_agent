from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
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


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    steps: List[Step]


# ✅ We pass employee_id when starting workflow (for manager resolution)
class StartWorkflow(BaseModel):
    employee_id: int


# ✅ Action now includes approver_id for security
class Action(BaseModel):
    approver_id: int
    remarks: str = ""


# ================================
# ✅ ROUTES – ADMIN MANAGEMENT
# ================================

@router.post("/create")
def create_workflow(req: WorkflowCreate):
    wf_id = workflow_db.create_workflow(
        req.name, req.module, [s.dict() for s in req.steps]
    )
    return {"message": "Workflow created", "workflow_id": wf_id}


@router.get("/all")
def list_workflows():
    """
    List all workflows (for admin UI table).
    """
    return workflow_db.get_all_workflows()


@router.get("/by-id/{workflow_id}")
def get_workflow_details(workflow_id: int):
    """
    Get workflow + steps for editing.
    """
    data = workflow_db.get_workflow_by_id(workflow_id)
    if not data:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return data


@router.put("/{workflow_id}")
def edit_workflow(workflow_id: int, req: WorkflowUpdate):
    """
    Edit workflow name & steps.
    ⚠️ Only allowed if workflow is NOT active.
    """
    try:
        steps = [s.dict() for s in req.steps]
        workflow_db.update_workflow(workflow_id, req.name, steps)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Workflow updated successfully"}


@router.post("/activate/{workflow_id}")
def activate(workflow_id: int):
    try:
        workflow_db.activate_workflow(workflow_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Workflow activated"}


@router.post("/deactivate/{workflow_id}")
def deactivate(workflow_id: int):
    try:
        workflow_db.deactivate_workflow(workflow_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Workflow deactivated"}


@router.delete("/{workflow_id}")
def delete_workflow(workflow_id: int):
    """
    Delete a workflow (only if no approval history).
    """
    try:
        workflow_db.delete_workflow(workflow_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Workflow deleted"}


@router.get("/active/{module}")
def get_active_for_module(module: str):
    """
    Get active workflow + steps for a given module (e.g., 'leave').
    Perfect for an admin preview UI.
    """
    data = workflow_db.get_active_workflow_with_steps(module)
    if not data:
        raise HTTPException(status_code=404, detail="No active workflow for this module")
    return data


# ================================
# ✅ APPROVER INBOX
# ================================
@router.get("/pending/{approver_id}")
def pending_for_approver(approver_id: int):
    """
    Get all pending approvals for a specific approver.
    Ideal for 'My Approvals' UI.
    """
    return workflow_db.get_pending_for_approver(approver_id)


# ================================
# ✅ ROUTES – RUNTIME EXECUTION
# ================================

# ✅ AUTO-START WORKFLOW (used by leaves / other modules)
@router.post("/{module}/start/{request_id}")
def start_workflow(module: str, request_id: int, req: StartWorkflow):
    wf = workflow_db.get_active_workflow(module)

    if not wf:
        raise HTTPException(status_code=404, detail="No active workflow found")

    try:
        result = workflow_db.start_workflow(
            module,
            request_id,
            wf["id"],
            req.employee_id   # ✅ used for manager resolution
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result


@router.post("/{module}/{request_id}/approve")
def approve(module: str, request_id: int, req: Action):
    """
    Approve current step for the given module & request.
    ✅ Enforces that approver_id matches the assigned approver.
    """
    try:
        result = workflow_db.approve_step(module, request_id, req.approver_id, req.remarks)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "message": "Step Approved",
        "result": result
    }


@router.post("/{module}/{request_id}/reject")
def reject(module: str, request_id: int, req: Action):
    """
    Reject current step.
    ✅ Enforces approver ownership.
    """
    try:
        workflow_db.reject_step(module, request_id, req.approver_id, req.remarks)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Rejected"}


@router.get("/{module}/{request_id}")
def get_status(module: str, request_id: int):
    return workflow_db.get_workflow_status(module, request_id)
