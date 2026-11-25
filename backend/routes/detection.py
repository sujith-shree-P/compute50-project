"""
SmartFlow AI - Vehicle & Image Detection API Routes
Handles single road, multi-road, combined intersection, ambulance detection,
and manual count adjustment.
"""

import time
import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Body
from backend.services.detector_service import DetectorService
from backend.models.schemas import (
    RoadDetectionResult,
    ImageAnalysisResponse,
    EmergencyVehicleDetectionResponse,
    VehicleCount,
    ManualAdjustmentRequest
)

router = APIRouter(prefix="/api/detect", tags=["Detection"])

# Initialize detector service singleton
detector_service = DetectorService()

# In-memory storage for active analyses
ANALYSIS_STORE: Dict[str, ImageAnalysisResponse] = {}

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB


def validate_file(file: UploadFile):
    filename = file.filename or ""
    ext = filename[filename.rfind("."):].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed: JPG, JPEG, PNG, WEBP."
        )


@router.post("/single", response_model=RoadDetectionResult)
async def detect_single(
    file: UploadFile = File(...),
    road_id: str = Form("north"),
    road_name: str = Form("North Approach"),
    conf_threshold: float = Form(0.25),
    capacity: int = Form(35)
):
    """
    Processes an individual uploaded image for a specific road direction.
    Uses real YOLOv8 inference with bounding boxes and per-category counts.
    """
    validate_file(file)
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 15MB limit.")
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        result = detector_service.detect_single_road(
            image_bytes=contents,
            road_id=road_id.lower(),
            road_name=road_name,
            conf_threshold=conf_threshold,
            capacity=capacity
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image processing failed: {str(e)}")


@router.post("/multi", response_model=ImageAnalysisResponse)
async def detect_multi(
    north_file: Optional[UploadFile] = File(None),
    south_file: Optional[UploadFile] = File(None),
    east_file: Optional[UploadFile] = File(None),
    west_file: Optional[UploadFile] = File(None),
    conf_threshold: float = Form(0.25),
    capacity: int = Form(35)
):
    """
    Processes up to 4 separate images representing North, South, East, and West roads.
    Every image is independently processed with genuine inference.
    Counts from unrelated images are never combined or guessed.
    """
    files_map = {
        "north": ("North Approach", north_file),
        "south": ("South Approach", south_file),
        "east": ("East Approach", east_file),
        "west": ("West Approach", west_file)
    }

    roads_result: Dict[str, RoadDetectionResult] = {}
    total_vehicles = 0
    start_time = time.time()

    active_count = 0
    for r_id, (name, file_obj) in files_map.items():
        if file_obj is not None:
            active_count += 1
            validate_file(file_obj)
            contents = await file_obj.read()
            if len(contents) == 0:
                continue

            r_res = detector_service.detect_single_road(
                image_bytes=contents,
                road_id=r_id,
                road_name=name,
                conf_threshold=conf_threshold,
                capacity=capacity
            )
            roads_result[r_id] = r_res
            total_vehicles += r_res.counts.total

    if active_count == 0:
        raise HTTPException(status_code=400, detail="Please upload at least one road image.")

    duration_ms = round((time.time() - start_time) * 1000.0, 1)
    analysis = ImageAnalysisResponse(
        analysis_id=f"multi_{uuid.uuid4().hex[:8]}",
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        roads=roads_result,
        total_vehicles_detected=total_vehicles,
        processing_time_ms=duration_ms,
        model_name="YOLOv8n (COCO Pretrained)",
        notes="Processed separate road images independently. Indian auto-rickshaws are typically recognized under light vehicle/car or motorcycle categories by general COCO models."
    )
    ANALYSIS_STORE[analysis.analysis_id] = analysis
    return analysis


@router.post("/combined", response_model=ImageAnalysisResponse)
async def detect_combined(
    file: UploadFile = File(...),
    conf_threshold: float = Form(0.25),
    capacity: int = Form(35)
):
    """
    Processes a combined intersection image showing a complete 2-way or 4-way junction.
    Partitions detections by road quadrant so counts are accurately distributed.
    """
    validate_file(file)
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        analysis = detector_service.detect_combined_intersection(
            image_bytes=contents,
            conf_threshold=conf_threshold,
            capacity=capacity
        )
        ANALYSIS_STORE[analysis.analysis_id] = analysis
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Combined image analysis failed: {str(e)}")


@router.post("/ambulance", response_model=EmergencyVehicleDetectionResponse)
async def detect_ambulance_endpoint(
    file: UploadFile = File(...),
    conf_threshold: float = Form(0.25)
):
    """
    Processes an uploaded emergency vehicle image.
    Performs AI inference, provides visual bounding box, and offers clear manual confirmation.
    """
    validate_file(file)
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        res = detector_service.detect_ambulance(
            image_bytes=contents,
            conf_threshold=conf_threshold
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Emergency vehicle detection failed: {str(e)}")


@router.post("/manual-adjust", response_model=RoadDetectionResult)
async def manual_adjust(req: ManualAdjustmentRequest):
    """
    Allows user to manually correct a missed or misclassified vehicle count for demonstration purposes.
    Clearly flags the result as 'is_user_adjusted = True' with audit trail.
    """
    analysis = ANALYSIS_STORE.get(req.analysis_id)
    if not analysis:
        # If not stored, synthesize response from counts
        road_id = req.road_id.lower()
        cnt = req.counts
        cnt.total = cnt.cars + cnt.motorcycles + cnt.buses + cnt.trucks + cnt.other
        pcu = (cnt.cars * 1.0) + (cnt.motorcycles * 0.5) + (cnt.buses * 2.2) + (cnt.trucks * 2.5) + (cnt.other * 1.0)
        cat, pct = detector_service.calculate_density(cnt.total, pcu, capacity=35)
        return RoadDetectionResult(
            road_id=road_id,
            road_name=f"{road_id.capitalize()} Approach",
            counts=cnt,
            is_user_adjusted=True,
            confidence_avg=1.0,
            traffic_density_category=cat,
            traffic_density_percentage=pct,
            pcu_score=round(pcu, 1)
        )

    if req.road_id not in analysis.roads:
        raise HTTPException(status_code=404, detail=f"Road '{req.road_id}' not found in analysis {req.analysis_id}")

    road_res = analysis.roads[req.road_id]
    original = road_res.original_counts or road_res.counts.model_copy()

    # Recalculate total and PCU
    new_counts = req.counts
    new_counts.total = new_counts.cars + new_counts.motorcycles + new_counts.buses + new_counts.trucks + new_counts.other
    pcu = (new_counts.cars * 1.0) + (new_counts.motorcycles * 0.5) + (new_counts.buses * 2.2) + (new_counts.trucks * 2.5) + (new_counts.other * 1.0)
    density_cat, density_pct = detector_service.calculate_density(new_counts.total, pcu, capacity=35)

    updated_road = RoadDetectionResult(
        road_id=road_res.road_id,
        road_name=road_res.road_name,
        counts=new_counts,
        is_user_adjusted=True,
        original_counts=original,
        confidence_avg=road_res.confidence_avg,
        detected_boxes=road_res.detected_boxes,
        annotated_image_base64=road_res.annotated_image_base64,
        traffic_density_category=density_cat,
        traffic_density_percentage=density_pct,
        pcu_score=round(pcu, 1)
    )

    analysis.roads[req.road_id] = updated_road
    analysis.total_vehicles_detected = sum(r.counts.total for r in analysis.roads.values())
    return updated_road


@router.get("/analysis/{analysis_id}", response_model=ImageAnalysisResponse)
async def get_analysis(analysis_id: str):
    if analysis_id not in ANALYSIS_STORE:
        raise HTTPException(status_code=404, detail=f"Analysis ID {analysis_id} not found.")
    return ANALYSIS_STORE[analysis_id]
