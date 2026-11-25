"""
SmartFlow AI - Pydantic Data Models & Schemas
Defines request and response structures for Vehicle Detection, Signal Timing,
Emergency Corridor, Direction Estimation, Distance-Based Travel Times, and Analytics.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class VehicleCount(BaseModel):
    cars: int = 0
    motorcycles: int = 0
    buses: int = 0
    trucks: int = 0
    other: int = 0
    total: int = 0


class DetectionBox(BaseModel):
    category: str
    confidence: float
    bbox: List[int]  # [x1, y1, x2, y2]


class RoadDetectionResult(BaseModel):
    road_id: str  # e.g. "north", "south", "east", "west" or custom name
    road_name: str
    counts: VehicleCount
    is_user_adjusted: bool = False
    original_counts: Optional[VehicleCount] = None
    confidence_avg: float = 0.0
    detected_boxes: List[DetectionBox] = []
    annotated_image_base64: Optional[str] = None
    traffic_density_category: str = "Low"  # Low, Medium, High
    traffic_density_percentage: float = 0.0
    pcu_score: float = 0.0  # Passenger Car Units


class ImageAnalysisResponse(BaseModel):
    analysis_id: str
    timestamp: str
    roads: Dict[str, RoadDetectionResult]
    total_vehicles_detected: int
    processing_time_ms: float
    model_name: str = "YOLOv8n"
    notes: Optional[str] = None


class ManualAdjustmentRequest(BaseModel):
    analysis_id: str
    road_id: str
    counts: VehicleCount


class SignalConfig(BaseModel):
    min_green_seconds: int = 15
    max_green_seconds: int = 60
    yellow_seconds: int = 3
    all_red_seconds: int = 2
    fixed_green_seconds: int = 30
    road_capacity: int = 35


class RoadSignalTiming(BaseModel):
    road_id: str
    road_name: str
    vehicle_count: int
    pcu_score: float
    density_category: str
    fixed_green_seconds: int
    adaptive_green_seconds: int
    yellow_seconds: int
    all_red_seconds: int
    time_saved_seconds: int
    congestion_reduction_pct: float


class AdaptiveSignalCalculationResponse(BaseModel):
    calculation_id: str
    timestamp: str
    config: SignalConfig
    total_cycle_time_fixed: int
    total_cycle_time_adaptive: int
    cycle_time_difference: int
    timings: Dict[str, RoadSignalTiming]
    ordered_sequence: List[str]  # e.g. ["north", "east", "south", "west"]
    summary_insight: str


# -------------------------------------------------------------
# UPGRADED EMERGENCY MODULE SCHEMAS
# -------------------------------------------------------------

class TravelTimeCalculation(BaseModel):
    route_distance_km: float
    normal_speed_kmh: float = 35.0
    emergency_speed_kmh: float = 55.0
    normal_travel_time_sec: float
    normal_travel_time_formatted: str  # e.g. "4m 15s"
    corridor_travel_time_sec: float
    corridor_travel_time_formatted: str  # e.g. "1m 42s"
    time_saved_sec: float
    time_saved_formatted: str  # e.g. "2m 33s"
    time_saved_percentage: float
    junctions_count: int
    normal_signal_delay_sec: float
    corridor_signal_delay_sec: float


class EmergencyVehicleDetectionResponse(BaseModel):
    image_id: str
    timestamp: str
    is_emergency_vehicle: bool
    detection_method: str  # "CUSTOM_YOLO_MODEL" or "HYBRID_VISION_YOLO_CV"
    confidence: float
    vehicle_type: str
    annotated_image_base64: Optional[str] = None
    status_message: str
    
    # Automatic Direction Estimation
    approach_road: str = "Unknown"  # "North", "South", "East", "West", "Unknown"
    intended_exit_road: str = "Unknown"
    direction_movement: str = "Unknown"  # e.g. "North -> South"
    direction_confidence: float = 0.0
    is_direction_confident: bool = False
    requires_user_confirmation: bool = True
    
    # Automatic Green Corridor Activation
    auto_activated: bool = False
    emergency_corridor_active: bool = False
    
    # Distance-based travel time metrics
    travel_time: Optional[TravelTimeCalculation] = None
    
    # Camera / Region details
    calibration_preset: str = "Standard 4-Way Intersection"
    analysis_notes: str = ""


class CameraCalibrationConfig(BaseModel):
    preset_name: str = "Standard 4-Way Intersection"
    auto_activation_threshold: float = 0.65
    direction_confidence_threshold: float = 0.60
    normal_speed_kmh: float = 35.0
    emergency_speed_kmh: float = 55.0
    quadrants: Dict[str, List[float]] = {
        "north": [0.0, 0.2, 0.45, 0.8],
        "south": [0.55, 0.2, 1.0, 0.8],
        "east":  [0.2, 0.55, 0.8, 1.0],
        "west":  [0.2, 0.0, 0.8, 0.45]
    }


class EmergencyActivationRequest(BaseModel):
    junction_id: str = "J2"
    approach_road: str = "North"  # Road A
    destination_junction: Optional[str] = "J3"
    exit_road: str = "South"  # Road B
    manual_confirmation: bool = True
    vehicle_id: Optional[str] = "AMB-108"
    speed_normal_kmh: float = 35.0
    speed_emergency_kmh: float = 55.0


class EmergencyCorridorState(BaseModel):
    active: bool = False
    emergency_id: Optional[str] = None
    vehicle_id: Optional[str] = None
    current_junction: str = "J2"
    approach_road: str = "North"
    exit_road: str = "South"
    destination_junction: str = "J3"
    route_path: List[str] = []
    signals: Dict[str, str] = {}  # {"North": "GREEN_PRIORITY", "South": "GREEN_COMPATIBLE", "East": "RED_LOCKED", "West": "RED_LOCKED"}
    phase: str = "IDLE"  # "IDLE", "TRANSITIONING_CLEARANCE", "ACTIVE_PRIORITY", "CLEARED"
    elapsed_seconds: int = 0
    estimated_remaining_time_seconds: int = 0
    travel_time: Optional[TravelTimeCalculation] = None
    cleared_at: Optional[str] = None
    auto_triggered: bool = False
    message: str = "Normal adaptive operation"


class RouteCalculationRequest(BaseModel):
    start_junction: str = "J1"
    destination_junction: str = "J3"
    avoid_congestion: bool = True
    speed_normal_kmh: float = 35.0
    speed_emergency_kmh: float = 55.0


class RouteCalculationResponse(BaseModel):
    start_junction: str
    destination_junction: str
    path: List[str]
    path_junction_names: List[str]
    total_distance_km: float
    estimated_time_normal_min: float
    estimated_time_corridor_min: float
    time_saved_min: float
    junctions_in_route: List[Dict[str, Any]]
    travel_time_details: Optional[TravelTimeCalculation] = None
