"""
SIF Sentinel — Pydantic schemas for health endpoint.
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    message: str
