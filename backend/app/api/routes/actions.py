"""
SIF Sentinel — Action Center Routes (Phase 16)
==============================================

Provides endpoints to manage HSE actions generated from safety observations.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.api_v1 import (
    ActionItem,
    ActionListResponse,
    UpdateActionStatusRequest,
)
from app.services.report_store import get_repository
from app.schemas.decision import PriorityLevel

logger = logging.getLogger("sif_sentinel.actions_api")

router = APIRouter()

@router.get(
    "",
    response_model=ActionListResponse,
    summary="List Trackable HSE Actions",
    description="Retrieve paginated list of HSE actions generated from high-priority safety observations.",
)
def list_actions(
    limit: int = Query(default=50, ge=1, le=200, description="Max actions per page"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="Filter by status (Open, Assigned, In Progress, Verification, Closed)"),
    priority: Optional[PriorityLevel] = Query(default=None, description="Filter by risk priority"),
) -> ActionListResponse:
    repo = get_repository()
    # InMemory lookup
    actions = repo.get_actions(limit=limit)
    
    # Try fetching from DB if DB persists more history than memory
    try:
        from app.db.session import SessionLocal
        from app.services.db_service import DatabaseService
        with SessionLocal() as db:
            db_actions = DatabaseService.get_actions(db, limit=limit)
            # Sync to dict if memory is empty
            if not actions and db_actions:
                actions = []
                for db_act in db_actions:
                    a = ActionItem(
                        id=db_act.id,
                        report_id=db_act.report_id,
                        title=db_act.title,
                        priority=db_act.priority,
                        status=db_act.status,
                        site_location=db_act.site_location,
                        assigned_to=db_act.assigned_to,
                        created_at=db_act.created_at,
                        updated_at=db_act.updated_at
                    )
                    actions.append(a)
    except Exception as e:
        logger.warning("Database fetch actions notice: %s", e)

    # Apply filters
    if status_filter:
        actions = [a for a in actions if a.status.lower() == status_filter.lower()]
    if priority:
        actions = [a for a in actions if a.priority == priority]

    return ActionListResponse(
        actions=actions,
        total=len(actions)
    )

@router.put(
    "/{action_id}/status",
    response_model=ActionItem,
    summary="Update Action Status",
    description="Transition the workflow status of an HSE action.",
)
def update_action_status(
    action_id: str,
    payload: UpdateActionStatusRequest
) -> ActionItem:
    repo = get_repository()
    action = repo.update_action_status(
        action_id=action_id,
        status=payload.status,
        assigned_to=payload.assigned_to
    )

    if not action:
        # Check DB before failing
        try:
            from app.db.session import SessionLocal
            from app.services.db_service import DatabaseService
            with SessionLocal() as db:
                db_action = DatabaseService.update_action_status(
                    db=db,
                    action_id=action_id,
                    status=payload.status,
                    assigned_to=payload.assigned_to
                )
                if db_action:
                    action = ActionItem(
                        id=db_action.id,
                        report_id=db_action.report_id,
                        title=db_action.title,
                        priority=db_action.priority,
                        status=db_action.status,
                        site_location=db_action.site_location,
                        assigned_to=db_action.assigned_to,
                        created_at=db_action.created_at,
                        updated_at=db_action.updated_at
                    )
        except Exception as e:
            logger.warning("DB update action notice: %s", e)
    else:
        # Action found in memory, also update DB
        try:
            from app.db.session import SessionLocal
            from app.services.db_service import DatabaseService
            with SessionLocal() as db:
                DatabaseService.update_action_status(
                    db=db,
                    action_id=action_id,
                    status=payload.status,
                    assigned_to=payload.assigned_to
                )
        except Exception as e:
            logger.warning("DB update action notice: %s", e)

    if not action:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action with ID '{action_id}' was not found.",
        )

    logger.info("Action %s status updated to %s", action_id, payload.status)
    return action
