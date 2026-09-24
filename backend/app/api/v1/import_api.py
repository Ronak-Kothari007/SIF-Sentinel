from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
import os
import uuid
import shutil
from pathlib import Path

from app.services.document_parser import document_parser
from app.schemas.decision import DecisionResult
from app.schemas.api_v1 import AnalyzeReportRequest
from app.api.v1.api import analyze_report, get_decision_engine

MAX_FILE_SIZE = 10 * 1024 * 1024 # 10MB

def sanitize_filename(filename: str) -> str:
    if not filename:
        return "unnamed_file"
    # Basic sanitization to prevent path traversal
    safe_name = os.path.basename(filename)
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in " ._-").strip()
    return safe_name if safe_name else "unnamed_file"

router = APIRouter()

STORAGE_DIR = Path("storage/originals")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

class BulkProcessRequest(BaseModel):
    items: List[Dict[str, Any]]  # Mapped columns, can include temp_file_id, source_file_name

class SingleProcessRequest(BaseModel):
    report_text: str
    metadata: Optional[Dict[str, str]] = None
    temp_file_id: Optional[str] = None
    source_file_name: Optional[str] = None
    original_extracted_data: Optional[Dict[str, Any]] = None
    user_corrected_data: Optional[Dict[str, Any]] = None

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    safe_filename = sanitize_filename(file.filename)
    
    # Optional: File size check could be added here if reading chunks, but FastAPI UploadFile limits can also be configured.
    # We will read into memory for parse_document, so check size here.
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")
        
    try:
        temp_id = str(uuid.uuid4())
        temp_path = STORAGE_DIR / f"temp_{temp_id}_{safe_filename}"
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Rewind file for parser
        await file.seek(0)
        
        result = await document_parser.parse_document(
            file_obj=file,
            filename=safe_filename,
            mime_type=file.content_type
        )
        
        extracted_metadata = {}
        if not result.get("is_tabular") and result.get("extracted_text"):
            from app.services.extractor import HybridSafetyExtractor
            extractor = HybridSafetyExtractor()
            ctx = extractor.extract(result["extracted_text"])
            extracted_metadata = {
                "activity": ctx.activity,
                "hazard": ctx.hazard,
                "barrier": ctx.barrier,
                "barrier_status": ctx.barrier_status,
                "location": ctx.location,
            }
            
        result["extracted_metadata"] = extracted_metadata
        result["temp_file_id"] = temp_id
        result["source_file_name"] = safe_filename
        return {"status": "success", "data": result}
        
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while parsing the document: {str(e)}"
        )

def _link_file_to_report(report_id: str, temp_file_id: str, source_file_name: str, corrected_data: Optional[Dict[str, Any]] = None):
    # Validate UUID format to prevent path traversal
    try:
        uuid_obj = uuid.UUID(temp_file_id, version=4)
    except ValueError:
        return # Invalid UUID, abort linking
        
    safe_source_name = sanitize_filename(source_file_name)
    temp_path = STORAGE_DIR / f"temp_{temp_file_id}_{safe_source_name}"
    
    # Ensure the path doesn't escape STORAGE_DIR
    try:
        temp_path = temp_path.resolve()
        if not str(temp_path).startswith(str(STORAGE_DIR.resolve())):
            return
    except Exception:
        return

    if temp_path.exists() and temp_path.is_file():
        final_path = STORAGE_DIR / f"{report_id}_{safe_source_name}"
        temp_path.rename(final_path)
        
        from app.db.session import SessionLocal
        from app.db.models import Report
        with SessionLocal() as db:
            report = db.query(Report).filter(Report.id == report_id).first()
            if report:
                report.source_file_name = source_file_name
                report.source_file_path = str(final_path)
                
                # Update with corrected metadata fields if present
                if corrected_data:
                    if corrected_data.get("report_type"):
                        report.report_type = corrected_data.get("report_type")
                    # location is updated below or via analyze_report
                
                db.commit()

@router.post("/process-text", response_model=DecisionResult)
async def process_imported_text(request: SingleProcessRequest):
    if not request.report_text.strip():
        raise HTTPException(status_code=400, detail="Report text is empty")
        
    try:
        custom_id = None
        if request.metadata and "report_id" in request.metadata:
            custom_id = request.metadata["report_id"]
            
        # If user corrected the location, pass it to analysis
        location = None
        if request.user_corrected_data and request.user_corrected_data.get("location"):
            location = request.user_corrected_data.get("location")
            
        req = AnalyzeReportRequest(
            report_text=request.report_text,
            report_id=custom_id,
            location=location
        )
        result = analyze_report(req)
        
        # Link file and update report_type in DB
        if request.temp_file_id and request.source_file_name:
            _link_file_to_report(result.report_id, request.temp_file_id, request.source_file_name, request.user_corrected_data)
            
        # Log Audit Trail for Import Correction
        if request.original_extracted_data or request.user_corrected_data:
            from app.db.session import SessionLocal
            from app.services.db_service import DatabaseService
            import json
            
            audit_details = {
                "file_uploaded": request.source_file_name,
                "original_extracted": request.original_extracted_data or {},
                "user_corrected": request.user_corrected_data or {},
            }
            try:
                with SessionLocal() as db:
                    DatabaseService.record_audit_log(
                        db=db,
                        action="IMPORT_CORRECTION",
                        entity_type="report",
                        entity_id=result.report_id,
                        actor_id="importer",
                        details=audit_details
                    )
            except Exception as e:
                pass # Non-blocking
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-bulk")
async def process_bulk_reports(request: BulkProcessRequest):
    if not request.items:
        raise HTTPException(status_code=400, detail="No items provided for bulk processing")
        
    results = []
    errors = []
    
    for idx, item in enumerate(request.items):
        try:
            report_text = item.get("report_text", "")
            if not report_text.strip():
                errors.append({"index": idx, "error": "Empty report_text"})
                continue
                
            report_id = item.get("report_id")
            req = AnalyzeReportRequest(
                report_text=report_text,
                report_id=report_id
            )
            result = analyze_report(req)
            
            temp_file_id = item.get("temp_file_id")
            source_file_name = item.get("source_file_name")
            if temp_file_id and source_file_name:
                _link_file_to_report(result.report_id, temp_file_id, source_file_name)
                
            results.append(result)
        except Exception as e:
            errors.append({"index": idx, "error": str(e)})
            
    return {
        "status": "partial" if errors and results else "success" if results else "error",
        "processed_count": len(results),
        "error_count": len(errors),
        "errors": errors,
        "results": [res.model_dump() for res in results]
    }
