"""
SmartFlow AI - Signal Management API Routes
Computes adaptive signal timings and provides configuration parameters.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Body
from pydantic import BaseModel
from backend.services.signal_service import SignalService
from backend.models.schemas import (
    SignalConfig,
    AdaptiveSignalCalculationResponse,
    VehicleCount
)

router = APIRouter(prefix="/api/signals", tags=["Signals"])
signal_service = SignalService()


class SignalCalculateRequest(BaseModel):
    roads: Dict[str, Dict[str, Any]]
    config: Optional[SignalConfig] = None


@router.post("/calculate", response_model=AdaptiveSignalCalculationResponse)
async def calculate_signals(payload: SignalCalculateRequest):
    """
    Calculates dynamic green signal durations based on detected or adjusted vehicle volumes.
    Compares against the fixed signal baseline.
    """
    config = payload.config or SignalConfig()
    result = signal_service.calculate_timings(payload.roads, config)
    return result


@router.get("/config", response_model=SignalConfig)
async def get_default_config():
    """Returns default adaptive signal timing parameters."""
    return SignalConfig()
