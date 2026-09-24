from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response, FileResponse
from typing import Any
import os
from pathlib import Path

from app.services.report_store import get_repository
from app.services.pdf_generator import generate_assessment_pdf
from app.db.session import SessionLocal
from app.db.models import Report

router = APIRouter()

@router.get("/{report_id}/download/assessment", summary="Download Safety Assessment PDF")
def download_assessment_pdf(report_id: str):
    """
    Generate and return a professional PDF safety assessment for a report.
    """
    from app.services.db_service import DatabaseService
    with SessionLocal() as db:
        res = DatabaseService.get_decision_result(db, report_id)
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with ID '{report_id}' was not found in the repository."
            )
            
        db_report = db.query(Report).filter(Report.id == report_id).first()
        source_file_name = db_report.source_file_name if db_report else None
        
        report_data = {
            "id": res.report_id,
            "source": res.report_text if not db_report else db_report.source,
            "source_file_name": source_file_name or "N/A",
            "location": db_report.location if db_report else "Unknown",
            "created_at": db_report.created_at if db_report else datetime.now(timezone.utc),
            "report_type": db_report.report_type if db_report else "near_miss",
            "report_text": res.report_text
        }
        
        # Check if there is an HSE review
        hse_review_data = None
        if res.hse_reviewed:
            hse_review_data = {
                "decision": res.review_decision,
                "reviewer_id": res.reviewer_id,
                "reviewed_at": res.reviewed_at,
                "comments": res.review_comments
            }
            
        pdf_bytes = generate_assessment_pdf(
            report_data=report_data,
            analysis_data=res.model_dump(),
            hse_review=hse_review_data,
            workflow_status=res.workflow_status,
            audit_trail=res.audit_trail
        )

    filename = f"Safety_Assessment_{report_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

@router.get("/{report_id}/download/original", summary="Download Original Source File")
def download_original_file(report_id: str):
    """
    Return the original uploaded file associated with a report.
    """
    with SessionLocal() as db:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report with ID '{report_id}' was not found."
            )
            
        if not report.source_file_path or not os.path.exists(report.source_file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original file is not available or was not uploaded for this report."
            )
            
        # Security: ensure the file path is within the designated storage directory
        try:
            target_path = Path(report.source_file_path).resolve()
            storage_dir = Path("storage/originals").resolve()
            if not str(target_path).startswith(str(storage_dir)):
                raise ValueError("Path traversal attempt detected")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied."
            )
            
        filename = report.source_file_name or os.path.basename(report.source_file_path)
        return FileResponse(
            path=report.source_file_path,
            filename=filename,
            content_disposition_type="attachment"
        )

from fastapi import Query
from app.schemas.decision import PriorityLevel
import pandas as pd
import io
from datetime import datetime, timezone

@router.get("/export/reports", summary="Export Reports to CSV or XLSX")
def export_reports(
    export_type: str = Query(default="current", description="'current' for filtered, 'all' for all records"),
    format: str = Query(default="csv", description="'csv' or 'xlsx'"),
    priority: str | None = Query(default=None, description="Filter by priority"),
    hazard: str | None = Query(default=None, description="Filter by hazard"),
    activity: str | None = Query(default=None, description="Filter by activity"),
):
    from app.services.db_service import DatabaseService
    
    # Determine limit
    limit = 10000 if export_type == "all" else 1000
    
    with SessionLocal() as db:
        reports, _ = DatabaseService.list_all(
            db=db,
            limit=limit,
            offset=0,
            priority=priority,
            hazard=hazard,
            activity=activity,
        )
        
        data = []
        
        report_ids = [r["report_id"] for r in reports]
        db_reports = db.query(Report).filter(Report.id.in_(report_ids)).all()
        db_map = {r.id: r for r in db_reports}
        
        for r in reports:
            db_r = db_map.get(r["report_id"])
            
            row = {
                "report_id": r["report_id"],
                "source_file": db_r.source_file_name if db_r and db_r.source_file_name else "N/A",
                "report_type": db_r.report_type if db_r else "near_miss",
                "location": db_r.location if db_r else "Unknown",
                "created_at": r["created_at"].isoformat() if r["created_at"] else "",
                "activity": r["final_activity"] or r["ai_activity"] or "",
                "hazard": r["final_hazard"] or r["ai_hazard"] or "",
                "barrier": r["final_barrier"] or r["ai_barrier"] or "",
                "barrier_status": r["barrier_status"] or "",
                "priority": r["final_priority"] or r["ai_priority"],
                "priority_score": r["priority_score"],
                "sif_probability": r["sif_probability"],
                "triggered_rules": f"{r['triggered_rules_count']} rules",
                "hse_reviewed": r["hse_reviewed"],
                "hse_decision": r["review_decision"] or "",
                "workflow_status": r["workflow_status"] or ""
            }
            data.append(row)
            
    df = pd.DataFrame(data)
    # Reorder columns explicitly to match user request
    columns_order = [
        "report_id", "source_file", "report_type", "location", "created_at",
        "activity", "hazard", "barrier", "barrier_status", "priority",
        "priority_score", "sif_probability", "triggered_rules", 
        "hse_reviewed", "hse_decision", "workflow_status"
    ]
    # In case df is empty, ensure columns exist
    if df.empty:
        df = pd.DataFrame(columns=columns_order)
    else:
        # Only include columns we defined above, in that order
        df = df[columns_order]

    date_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    if format.lower() == "xlsx":
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Reports")
        buffer.seek(0)
        
        filename = f"SIF_Sentinel_Report_Register_{date_str}.xlsx"
        return Response(
            content=buffer.read(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    else:
        # Default to CSV
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        
        filename = f"SIF_Sentinel_Report_Register_{date_str}.csv"
        return Response(
            content=buffer.read(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
