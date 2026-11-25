"""
SmartFlow AI - Emergency Green Corridor API Routes
Handles emergency vehicle activation, Dijkstra routing between junctions,
signal priority coordination, and phase clearing.
"""

from typing import List, Dict, Any
from fastapi import APIRouter
from backend.services.emergency_service import (
    EmergencyService,
    JUNCTION_INFO,
    NETWORK_EDGES
)
from backend.models.schemas import (
    EmergencyActivationRequest,
    EmergencyCorridorState,
    RouteCalculationRequest,
    RouteCalculationResponse
)

router = APIRouter(prefix="/api/emergency", tags=["Emergency Corridor"])
emergency_service = EmergencyService()


@router.post("/activate", response_model=EmergencyCorridorState)
async def activate_corridor(req: EmergencyActivationRequest):
    """
    Activates the emergency vehicle green corridor.
    Applies the 4-road conflict logic:
    - Ambulance Approach (A): GREEN_PRIORITY
    - Cross Traffic (C & D): RED_LOCKED
    - Compatible Opposing Approach (B): GREEN_COMPATIBLE
    """
    return emergency_service.activate_corridor(req)


@router.post("/clear", response_model=EmergencyCorridorState)
async def clear_corridor():
    """
    Marks the ambulance as cleared.
    Safely terminates priority and resumes adaptive traffic control.
    """
    return emergency_service.clear_corridor()


@router.get("/status", response_model=EmergencyCorridorState)
async def get_status():
    """Returns the current real-time state of the emergency green corridor."""
    return emergency_service.get_status()


@router.post("/route", response_model=RouteCalculationResponse)
async def calculate_route(req: RouteCalculationRequest):
    """
    Executes Dijkstra's algorithm to determine the fastest emergency corridor route
    across connected junctions in the simulated network.
    """
    return emergency_service.compute_dijkstra_route(
        start=req.start_junction,
        destination=req.destination_junction,
        avoid_congestion=req.avoid_congestion
    )


@router.get("/network")
async def get_network():
    """Returns all simulated road network junctions and connecting links."""
    links = [
        {
            "from": u,
            "to": v,
            "distance_km": dist,
            "speed_kmh": spd,
            "congestion_factor": cong
        }
        for u, v, dist, spd, cong in NETWORK_EDGES
    ]
    return {
        "junctions": list(JUNCTION_INFO.values()),
        "links": links
    }


@router.get("/history")
async def get_history():
    """Returns log of historical emergency corridor activation events."""
    return emergency_service.get_history()
