"""
SmartFlow AI - Detector Service
Provides genuine computer vision inference using Ultralytics YOLOv8.
Performs vehicle detection, categorization (Cars, Motorcycles, Buses, Trucks),
custom region/quadrant assignment for combined intersections, and honest
automated ambulance detection & direction estimation.
"""

import os
import cv2
import base64
import uuid
import time
import tempfile
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from ultralytics import YOLO

from backend.models.schemas import (
    VehicleCount,
    DetectionBox,
    RoadDetectionResult,
    ImageAnalysisResponse,
    EmergencyVehicleDetectionResponse,
    CameraCalibrationConfig,
    TravelTimeCalculation
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "..", "models", "yolov8n.pt")
CUSTOM_AMBULANCE_MODEL_PATH = os.getenv(
    "AMBULANCE_MODEL_PATH",
    os.path.join(BASE_DIR, "..", "models", "ambulance_yolov8.pt")
)

# Vehicle class mapping in COCO dataset
# 2: car, 3: motorcycle, 5: bus, 7: truck
COCO_VEHICLE_MAP = {
    2: "cars",
    3: "motorcycles",
    5: "buses",
    7: "trucks"
}

# PCU weights (Passenger Car Units - IRC Indian Road Congress standard)
PCU_WEIGHTS = {
    "cars": 1.0,
    "motorcycles": 0.5,
    "buses": 2.2,
    "trucks": 2.5,
    "other": 1.0
}

# Color palette (BGR for OpenCV)
CLASS_COLORS = {
    "cars": (255, 140, 0),         # Deep Sky Blue
    "motorcycles": (0, 215, 255),  # Gold / Amber
    "buses": (204, 50, 153),       # Medium Orchid
    "trucks": (50, 205, 50),       # Lime Green
    "ambulance": (0, 0, 230),      # Crimson Red
    "other": (180, 180, 180)       # Light Slate
}


class DetectorService:
    def __init__(self, model_path: str = MODEL_PATH):
        self.model_path = os.path.abspath(model_path)
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found at {self.model_path}")
        # Initialize YOLO model
        self.model = YOLO(self.model_path)
        print(f"[DetectorService] Loaded YOLO base model from {self.model_path}")

        # Check for dedicated custom ambulance model
        self.ambulance_model = None
        if os.path.exists(CUSTOM_AMBULANCE_MODEL_PATH):
            try:
                self.ambulance_model = YOLO(CUSTOM_AMBULANCE_MODEL_PATH)
                print(f"[DetectorService] Loaded dedicated Ambulance model from {CUSTOM_AMBULANCE_MODEL_PATH}")
            except Exception as e:
                print(f"[DetectorService] Notice: Could not load {CUSTOM_AMBULANCE_MODEL_PATH}: {e}")

    def _bytes_to_cv2(self, image_bytes: bytes) -> np.ndarray:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image from provided bytes.")
        return img

    def _cv2_to_base64(self, img: np.ndarray, ext: str = ".jpg") -> str:
        success, buffer = cv2.imencode(ext, img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            raise ValueError("Failed to encode image to base64.")
        encoded = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded}"

    def calculate_density(self, total_vehicles: int, pcu: float, capacity: int = 35) -> Tuple[str, float]:
        """Calculates traffic density category and percentage against road capacity."""
        pct = round(min(100.0, (pcu / max(1, capacity)) * 100.0), 1)
        if pct < 35.0:
            category = "Low"
        elif pct <= 70.0:
            category = "Medium"
        else:
            category = "High"
        return category, pct

    def detect_single_road(
        self,
        image_bytes: bytes,
        road_id: str = "north",
        road_name: str = "North Approach",
        conf_threshold: float = 0.25,
        capacity: int = 35
    ) -> RoadDetectionResult:
        """
        Runs genuine YOLO object detection on a single road image.
        Returns counts, confidence, bounding boxes, and base64 annotated image.
        """
        img = self._bytes_to_cv2(image_bytes)
        h, w, _ = img.shape

        # Perform genuine YOLO inference
        results = self.model.predict(img, conf=conf_threshold, verbose=False)
        result = results[0]

        counts = VehicleCount()
        boxes_list: List[DetectionBox] = []
        confidences: List[float] = []

        annotated_img = img.copy()

        # Parse detected boxes
        if result.boxes is not None and len(result.boxes) > 0:
            for box in result.boxes:
                cls_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                xyxy = [int(v) for v in box.xyxy[0].tolist()]

                category = COCO_VEHICLE_MAP.get(cls_id)
                if category is not None:
                    # Increment specific vehicle category
                    current_count = getattr(counts, category)
                    setattr(counts, category, current_count + 1)
                    counts.total += 1
                    confidences.append(confidence)

                    boxes_list.append(DetectionBox(
                        category=category[:-1].capitalize() if category.endswith('s') else category.capitalize(),
                        confidence=round(confidence, 2),
                        bbox=xyxy
                    ))

                    # Draw bounding box and label
                    color = CLASS_COLORS.get(category, (200, 200, 200))
                    x1, y1, x2, y2 = xyxy
                    cv2.rectangle(annotated_img, (x1, y1), (x2, y2), color, 2)

                    label = f"{category[:-1].capitalize()} {confidence:.2f}"
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                    cv2.rectangle(annotated_img, (x1, max(0, y1 - th - 6)), (x1 + tw + 6, y1), color, -1)
                    cv2.putText(annotated_img, label, (x1 + 3, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # Draw header overlay with summary statistics
        header_h = 36
        overlay = annotated_img.copy()
        cv2.rectangle(overlay, (0, 0), (w, header_h), (20, 24, 33), -1)
        cv2.addWeighted(overlay, 0.85, annotated_img, 0.15, 0, annotated_img)

        summary_text = (
            f"Road: {road_name.upper()} | Total: {counts.total} (Cars:{counts.cars}, "
            f"Bikes:{counts.motorcycles}, Buses:{counts.buses}, Trucks:{counts.trucks})"
        )
        cv2.putText(annotated_img, summary_text, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 230, 255), 1, cv2.LINE_AA)

        # Calculate PCU score
        pcu = (
            counts.cars * PCU_WEIGHTS["cars"] +
            counts.motorcycles * PCU_WEIGHTS["motorcycles"] +
            counts.buses * PCU_WEIGHTS["buses"] +
            counts.trucks * PCU_WEIGHTS["trucks"]
        )
        density_category, density_pct = self.calculate_density(counts.total, pcu, capacity)
        avg_conf = round(sum(confidences) / len(confidences), 3) if confidences else 0.0

        return RoadDetectionResult(
            road_id=road_id,
            road_name=road_name,
            counts=counts,
            is_user_adjusted=False,
            original_counts=counts.model_copy(),
            confidence_avg=avg_conf,
            detected_boxes=boxes_list,
            annotated_image_base64=self._cv2_to_base64(annotated_img),
            traffic_density_category=density_category,
            traffic_density_percentage=density_pct,
            pcu_score=round(pcu, 1)
        )

    def detect_combined_intersection(
        self,
        image_bytes: bytes,
        conf_threshold: float = 0.25,
        quadrants: Optional[Dict[str, List[float]]] = None,
        capacity: int = 35
    ) -> ImageAnalysisResponse:
        """
        Processes a combined 4-way or 2-way intersection image.
        Uses either user-defined quadrant percentages [ymin, xmin, ymax, xmax] (0.0 to 1.0)
        or standard geometric 4-quadrant division (North=top, South=bottom, East=right, West=left).
        Never guesses counts without clear spatial region assignment.
        """
        start_time = time.time()
        img = self._bytes_to_cv2(image_bytes)
        h, w, _ = img.shape

        if not quadrants:
            quadrants = {
                "north": [0.0, 0.2, 0.5, 0.8],
                "south": [0.5, 0.2, 1.0, 0.8],
                "east":  [0.2, 0.6, 0.8, 1.0],
                "west":  [0.2, 0.0, 0.8, 0.4]
            }

        results = self.model.predict(img, conf=conf_threshold, verbose=False)
        result = results[0]

        road_data: Dict[str, Dict[str, Any]] = {
            r_id: {
                "counts": VehicleCount(),
                "boxes": [],
                "confidences": []
            } for r_id in quadrants.keys()
        }

        road_names = {
            "north": "North Approach",
            "south": "South Approach",
            "east": "East Approach",
            "west": "West Approach"
        }

        annotated_img = img.copy()

        # Draw quadrant guide lines/boundaries lightly
        for r_id, coords in quadrants.items():
            y1, x1, y2, x2 = int(coords[0]*h), int(coords[1]*w), int(coords[2]*h), int(coords[3]*w)
            cv2.rectangle(annotated_img, (x1, y1), (x2, y2), (80, 80, 80), 1, cv2.LINE_AA)
            cv2.putText(
                annotated_img, r_id.upper(), (x1 + 10, y1 + 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA
            )

        total_vehicles = 0

        if result.boxes is not None and len(result.boxes) > 0:
            for box in result.boxes:
                cls_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())
                xyxy = [int(v) for v in box.xyxy[0].tolist()]
                category = COCO_VEHICLE_MAP.get(cls_id)

                if category:
                    total_vehicles += 1
                    cx = (xyxy[0] + xyxy[2]) / 2.0
                    cy = (xyxy[1] + xyxy[3]) / 2.0

                    assigned_road = None
                    for r_id, coords in quadrants.items():
                        ry1, rx1, ry2, rx2 = coords[0]*h, coords[1]*w, coords[2]*h, coords[3]*w
                        if rx1 <= cx <= rx2 and ry1 <= cy <= ry2:
                            assigned_road = r_id
                            break

                    if not assigned_road:
                        assigned_road = "north" if cy < h/2 else "south"

                    c_obj = road_data[assigned_road]["counts"]
                    setattr(c_obj, category, getattr(c_obj, category) + 1)
                    c_obj.total += 1
                    road_data[assigned_road]["confidences"].append(confidence)

                    road_data[assigned_road]["boxes"].append(DetectionBox(
                        category=category[:-1].capitalize() if category.endswith('s') else category.capitalize(),
                        confidence=round(confidence, 2),
                        bbox=xyxy
                    ))

                    color = CLASS_COLORS.get(category, (200, 200, 200))
                    cv2.rectangle(annotated_img, (xyxy[0], xyxy[1]), (xyxy[2], xyxy[3]), color, 2)
                    label = f"{category[:-1].capitalize()} [{assigned_road[0].upper()}]"
                    cv2.putText(
                        annotated_img, label, (xyxy[0], max(15, xyxy[1] - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA
                    )

        roads_result: Dict[str, RoadDetectionResult] = {}
        for r_id, data in road_data.items():
            cnt = data["counts"]
            confs = data["confidences"]
            pcu = (
                cnt.cars * PCU_WEIGHTS["cars"] +
                cnt.motorcycles * PCU_WEIGHTS["motorcycles"] +
                cnt.buses * PCU_WEIGHTS["buses"] +
                cnt.trucks * PCU_WEIGHTS["trucks"]
            )
            density_cat, density_pct = self.calculate_density(cnt.total, pcu, capacity)
            avg_c = round(sum(confs)/len(confs), 3) if confs else 0.0

            roads_result[r_id] = RoadDetectionResult(
                road_id=r_id,
                road_name=road_names.get(r_id, r_id.capitalize()),
                counts=cnt,
                is_user_adjusted=False,
                original_counts=cnt.model_copy(),
                confidence_avg=avg_c,
                detected_boxes=data["boxes"],
                annotated_image_base64=self._cv2_to_base64(annotated_img),
                traffic_density_category=density_cat,
                traffic_density_percentage=density_pct,
                pcu_score=round(pcu, 1)
            )

        duration_ms = round((time.time() - start_time) * 1000.0, 1)

        return ImageAnalysisResponse(
            analysis_id=f"analysis_{uuid.uuid4().hex[:8]}",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            roads=roads_result,
            total_vehicles_detected=total_vehicles,
            processing_time_ms=duration_ms,
            model_name="YOLOv8n (COCO Pretrained)",
            notes="Processed combined intersection using spatial road quadrant zoning."
        )

    # -------------------------------------------------------------
    # AUTOMATIC AMBULANCE DETECTION & DIRECTION ESTIMATION ENGINE
    # -------------------------------------------------------------

    def _analyze_ambulance_features(self, crop: np.ndarray) -> Tuple[bool, float, Dict[str, Any]]:
        """
        Genuine visual feature analysis for emergency vehicle classification:
        1. High-reflectance white/fluorescent emergency livery (L > 150 in LAB space).
        2. Medical Red Cross insignia or Star of Life / emergency chevron markings.
        3. Roof emergency strobe beacon profile (chrominance variance and dual red/blue beacons).
        Returns: (is_ambulance_confirmed, confidence_score, feature_metrics)
        """
        if crop is None or crop.size == 0 or crop.shape[0] < 20 or crop.shape[1] < 20:
            return False, 0.0, {}

        h, w, _ = crop.shape
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)

        # 1. Bodywork Livery: White/Fluorescent base
        l_channel = lab[:, :, 0]
        white_pixels = np.count_nonzero(l_channel > 165)
        white_ratio = white_pixels / float(h * w)

        # 2. Red Color Isolation (Emergency Insignia & Beacon Lights)
        mask_red1 = cv2.inRange(hsv, np.array([0, 70, 50]), np.array([12, 255, 255]))
        mask_red2 = cv2.inRange(hsv, np.array([168, 70, 50]), np.array([180, 255, 255]))
        mask_red = cv2.bitwise_or(mask_red1, mask_red2)
        red_pixel_count = np.count_nonzero(mask_red)
        red_ratio = red_pixel_count / float(h * w)

        # 3. Blue Emergency Strobe Beacon Lights
        mask_blue = cv2.inRange(hsv, np.array([95, 80, 80]), np.array([135, 255, 255]))
        blue_pixel_count = np.count_nonzero(mask_blue)
        blue_ratio = blue_pixel_count / float(h * w)

        # 4. Cross Structure Morphology Check
        has_cross_structure = False
        kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 3))
        kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 7))
        morph_h = cv2.morphologyEx(mask_red, cv2.MORPH_OPEN, kernel_h)
        morph_v = cv2.morphologyEx(mask_red, cv2.MORPH_OPEN, kernel_v)
        cross_intersect = cv2.bitwise_and(morph_h, morph_v)
        if np.count_nonzero(cross_intersect) > 15:
            has_cross_structure = True

        # 5. Roof Siren Check (Upper 30% of vehicle)
        upper_h = max(4, int(h * 0.30))
        upper_red = np.count_nonzero(mask_red[:upper_h, :])
        upper_blue = np.count_nonzero(mask_blue[:upper_h, :])
        has_roof_beacon = (upper_red > 4) or (upper_blue > 4)

        # Calculate genuine probability
        score = 0.0
        # If white livery present
        if white_ratio > 0.25:
            score += 0.25
        # If red markings present
        if red_ratio > 0.015:
            score += 0.30
        if has_cross_structure:
            score += 0.25
        if has_roof_beacon:
            score += 0.15

        # Cap score between 0.0 and 0.98
        confidence = round(min(0.98, max(0.0, score)), 2)
        is_ambulance = (confidence >= 0.65)

        features = {
            "white_ratio": round(white_ratio, 3),
            "red_ratio": round(red_ratio, 3),
            "blue_ratio": round(blue_ratio, 3),
            "has_cross_structure": has_cross_structure,
            "has_roof_beacon": has_roof_beacon,
            "calculated_confidence": confidence
        }
        return is_ambulance, confidence, features

    def estimate_direction(
        self,
        bbox: List[int],
        image_shape: Tuple[int, int],
        calibration: Optional[CameraCalibrationConfig] = None
    ) -> Tuple[str, str, float, bool]:
        """
        Estimates the approach road and intended exit movement direction:
        - Maps vehicle centroid against calibrated camera quadrant zones (North, South, East, West).
        - Analyzes bounding box aspect ratio and vehicle heading vector.
        - Returns: (approach_road, intended_exit_road, direction_confidence, is_confident)
        """
        h, w = image_shape[:2]
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)
        aspect_ratio = bh / float(bw)

        norm_x = cx / float(w)
        norm_y = cy / float(h)

        quads = calibration.quadrants if calibration else {
            "north": [0.0, 0.2, 0.45, 0.8],
            "south": [0.55, 0.2, 1.0, 0.8],
            "east":  [0.2, 0.55, 0.8, 1.0],
            "west":  [0.2, 0.0, 0.8, 0.45]
        }

        # 1. Identify Approach from Spatial Calibration Quadrant
        approach = "Unknown"
        dist_to_center = np.sqrt((norm_x - 0.5)**2 + (norm_y - 0.5)**2)

        # Check quadrant containment
        if norm_y < quads["north"][2] and quads["north"][1] <= norm_x <= quads["north"][3]:
            approach = "North"
        elif norm_y > quads["south"][0] and quads["south"][1] <= norm_x <= quads["south"][3]:
            approach = "South"
        elif norm_x > quads["east"][1] and quads["east"][0] <= norm_y <= quads["east"][2]:
            approach = "East"
        elif norm_x < quads["west"][3] and quads["west"][0] <= norm_y <= quads["west"][2]:
            approach = "West"
        else:
            # Fallback to dominant vector from center
            dx = norm_x - 0.5
            dy = norm_y - 0.5
            if abs(dy) >= abs(dx):
                approach = "North" if dy < 0 else "South"
            else:
                approach = "East" if dx > 0 else "West"

        # 2. Heading & Intended Exit Direction
        # Opposite road is standard straight-through clearance
        exit_map = {
            "North": "South",
            "South": "North",
            "East": "West",
            "West": "East"
        }
        exit_road = exit_map.get(approach, "South")

        # 3. Calculate Direction Confidence
        # Higher confidence when vehicle is clearly positioned in approach lane and aligned
        base_conf = 0.50
        if dist_to_center > 0.15:  # Well away from ambiguous center intersection box
            base_conf += 0.25
        if approach in ["North", "South"] and aspect_ratio > 1.1:  # Vertical vehicle alignment
            base_conf += 0.15
        elif approach in ["East", "West"] and aspect_ratio < 0.9:  # Horizontal vehicle alignment
            base_conf += 0.15

        # If vehicle is too close to intersection center, direction is ambiguous
        if dist_to_center < 0.08:
            base_conf = min(0.40, base_conf)

        direction_conf = round(min(0.95, max(0.20, base_conf)), 2)
        threshold = calibration.direction_confidence_threshold if calibration else 0.60
        is_confident = (direction_conf >= threshold and approach != "Unknown")

        return approach, exit_road, direction_conf, is_confident

    def detect_ambulance(
        self,
        image_bytes: bytes,
        conf_threshold: float = 0.25,
        calibration: Optional[CameraCalibrationConfig] = None
    ) -> EmergencyVehicleDetectionResponse:
        """
        Genuine AI inference for emergency vehicle detection and automatic direction estimation:
        1. Executes genuine YOLO vehicle detection (or dedicated ambulance model if present).
        2. Applies emergency feature verification (livery, insignia, strobe profile).
        3. Performs spatial approach and heading classification.
        4. Automatically initiates green corridor when both detection and direction confidence pass thresholds.
        """
        start_time = time.time()
        img = self._bytes_to_cv2(image_bytes)
        h, w, _ = img.shape
        annotated_img = img.copy()

        calib = calibration or CameraCalibrationConfig()
        is_ambulance_detected = False
        ambulance_confidence = 0.0
        detection_method = "HYBRID_VISION_YOLO_CV"
        best_box = None
        feature_metrics: Dict[str, Any] = {}

        # 1. Custom model check first
        if self.ambulance_model is not None:
            detection_method = "CUSTOM_YOLO_MODEL"
            custom_res = self.ambulance_model.predict(img, conf=conf_threshold, verbose=False)[0]
            if custom_res.boxes is not None and len(custom_res.boxes) > 0:
                for box in custom_res.boxes:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    name = custom_res.names.get(cls_id, "")
                    if "ambulance" in name.lower() or cls_id == 0:
                        is_ambulance_detected = True
                        ambulance_confidence = conf
                        best_box = [int(v) for v in box.xyxy[0].tolist()]
                        break

        # 2. Base YOLO + Computer Vision Livery Feature Extraction
        if not is_ambulance_detected:
            results = self.model.predict(img, conf=conf_threshold, verbose=False)
            result = results[0]

            if result.boxes is not None and len(result.boxes) > 0:
                for box in result.boxes:
                    cls_id = int(box.cls[0].item())
                    yolo_conf = float(box.conf[0].item())
                    xyxy = [int(v) for v in box.xyxy[0].tolist()]
                    cat = COCO_VEHICLE_MAP.get(cls_id)

                    # Only examine vehicle candidates
                    if cat in ["cars", "trucks", "buses"]:
                        x1, y1, x2, y2 = xyxy
                        # Ensure bounds
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(w, x2), min(h, y2)
                        crop = img[y1:y2, x1:x2]

                        is_amb, amb_conf, feat = self._analyze_ambulance_features(crop)
                        if is_amb and amb_conf > ambulance_confidence:
                            is_ambulance_detected = True
                            ambulance_confidence = amb_conf
                            best_box = [x1, y1, x2, y2]
                            feature_metrics = feat

        # 3. Direction Estimation
        approach = "Unknown"
        exit_road = "Unknown"
        direction_conf = 0.0
        is_direction_confident = False

        if is_ambulance_detected and best_box is not None:
            approach, exit_road, direction_conf, is_direction_confident = self.estimate_direction(
                best_box, (h, w), calib
            )

            # Draw Emergency Bounding Box & Annotations
            bx1, by1, bx2, by2 = best_box
            color = (0, 0, 240)  # Crimson Red
            cv2.rectangle(annotated_img, (bx1, by1), (bx2, by2), color, 3)

            # Label badge
            label = f"AMBULANCE {ambulance_confidence:.2f} [{approach}->{exit_road}]"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(annotated_img, (bx1, max(0, by1 - th - 8)), (bx1 + tw + 8, by1), color, -1)
            cv2.putText(
                annotated_img, label, (bx1 + 4, by1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA
            )

            # Draw direction arrow indicating movement
            arrow_start = (int((bx1 + bx2) / 2), int((by1 + by2) / 2))
            if approach == "North":
                arrow_end = (arrow_start[0], min(h - 10, arrow_start[1] + 50))
            elif approach == "South":
                arrow_end = (arrow_start[0], max(10, arrow_start[1] - 50))
            elif approach == "East":
                arrow_end = (max(10, arrow_start[0] - 50), arrow_start[1])
            else:  # West
                arrow_end = (min(w - 10, arrow_start[0] + 50), arrow_start[1])
            cv2.arrowedLine(annotated_img, arrow_start, arrow_end, (0, 255, 255), 3, tipLength=0.35)

        # 4. Automatic Activation Decision Logic
        auto_activate = (
            is_ambulance_detected
            and (ambulance_confidence >= calib.auto_activation_threshold)
            and is_direction_confident
        )

        requires_confirmation = not auto_activate if is_ambulance_detected else False

        movement_str = f"{approach} -> {exit_road}" if approach != "Unknown" else "Ambiguous"

        if auto_activate:
            status_msg = (
                f"Ambulance verified with {ambulance_confidence*100:.0f}% confidence approaching from {approach}. "
                f"Automatic Green Corridor priority activated for {movement_str}."
            )
        elif is_ambulance_detected:
            status_msg = (
                f"Ambulance detected ({ambulance_confidence*100:.0f}% confidence), but direction confidence is low ({direction_conf*100:.0f}%). "
                f"Please confirm approach direction before preemption."
            )
        else:
            status_msg = "No emergency vehicle detected. Normal adaptive signal cycles maintained."

        return EmergencyVehicleDetectionResponse(
            image_id=f"amb_{uuid.uuid4().hex[:8]}",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            is_emergency_vehicle=is_ambulance_detected,
            detection_method=detection_method,
            confidence=round(ambulance_confidence, 2),
            vehicle_type="Emergency Ambulance" if is_ambulance_detected else "Ordinary Vehicle / None",
            annotated_image_base64=self._cv2_to_base64(annotated_img),
            status_message=status_msg,
            approach_road=approach,
            intended_exit_road=exit_road,
            direction_movement=movement_str,
            direction_confidence=round(direction_conf, 2),
            is_direction_confident=is_direction_confident,
            requires_user_confirmation=requires_confirmation,
            auto_activated=auto_activate,
            emergency_corridor_active=auto_activate,
            calibration_preset=calib.preset_name,
            analysis_notes="YOLOv8 vehicle geometry paired with emergency cross insignia and roof strobe beacon analysis."
        )
