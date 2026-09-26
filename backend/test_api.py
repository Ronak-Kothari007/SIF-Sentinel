import os
os.environ['DISABLE_AI_MODELS'] = 'true'
from app.db.session import SessionLocal, init_db
init_db()
from app.services.db_service import DatabaseService
from app.services.report_store import get_repository
from app.schemas.api_v1 import PatternAnalysisResponse
with SessionLocal() as db:
    db_patterns = DatabaseService.get_patterns(db)
    repo = get_repository()
    semantic_patterns = repo.get_patterns().semantic_patterns
    db_patterns["semantic_patterns"] = semantic_patterns
    try:
        resp = PatternAnalysisResponse(**db_patterns)
        print("SUCCESS")
    except Exception as e:
        print("ERROR:", e)
