import os
os.environ['DISABLE_AI_MODELS'] = 'true'
from app.services.report_store import get_repository
repo = get_repository()
print(repo.get_patterns())
