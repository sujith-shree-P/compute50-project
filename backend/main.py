from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
import cv2, numpy as np, tempfile, os

app = FastAPI(title="SmartTraffic AI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

_model = None
VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck"}
def get_model():
    global _model
    if _model is None:
        try:
            _model = YOLO("yolov8n.pt")
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Could not load YOLO model: {exc}")
    return _model

def analyze_image_bytes(data: bytes):
    arr = np.frombuffer(data, np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="File is not a readable image/frame.")
    model = get_model()
    result = model.predict(frame, imgsz=1280, conf=0.20, verbose=False)[0]
    counts = {name: 0 for name in sorted(VEHICLE_CLASSES)}
    detections = []
    direction_counts = {
        "north": 0,
        "south": 0,
        "east": 0,
        "west": 0
    }
    names = result.names
    if result.boxes is not None:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            label = names.get(cls_id, str(cls_id))
            if label in VEHICLE_CLASSES:
                counts[label] += 1
                x1, y1, x2, y2 = [round(float(v), 1) for v in box.xyxy[0]]
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2

                width = frame.shape[1]
                height = frame.shape[0]

                if center_x < width / 2 and center_y < height / 2:
                    direction_counts["north"] += 1
                elif center_x >= width / 2 and center_y < height / 2:
                    direction_counts["east"] += 1
                elif center_x < width / 2 and center_y >= height / 2:
                    direction_counts["west"] += 1
                else:
                    direction_counts["south"] += 1

                detections.append({
                    "label": label,
                    "confidence": round(float(box.conf[0]), 3),
                    "box": [x1, y1, x2, y2]
                })
    total = sum(counts.values())
    level = "Low" if total < 8 else "Medium" if total < 20 else "High"
    return {
        "vehicle_count": total,
        "counts": counts,
        "direction_counts": direction_counts,
        "density": level,
        "detections": detections,
        "frame_width": int(frame.shape[1]),
        "frame_height": int(frame.shape[0])
    }
@app.get("/")
def root():
    return {"name": "SmartTraffic AI API", "status": "running"}

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image exceeds 15 MB limit.")
    return analyze_image_bytes(data)

@app.post("/api/analyze-frame")
async def analyze_frame(file: UploadFile = File(...)):
    data = await file.read()
    return analyze_image_bytes(data)

@app.post("/api/analyze-video")
async def analyze_video(file: UploadFile = File(...)):
    suffix = os.path.splitext(file.filename or "clip.mp4")[1] or ".mp4"
    data = await file.read()
    if len(data) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Video exceeds 100 MB limit.")
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data); tmp_path = tmp.name
        cap = cv2.VideoCapture(tmp_path)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Could not read this video. Try MP4.")
        fps = cap.get(cv2.CAP_PROP_FPS) or 1
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = round(total_frames / fps, 1) if total_frames else 0
        samples, frame_idx = [], 0
        # Sample at most 8 frames to keep the hackathon prototype responsive.
        while len(samples) < 8:
            ok, frame = cap.read()
            if not ok: break
            if frame_idx % max(1, int(fps * max(duration / 8, 1))) == 0:
                ok, encoded = cv2.imencode(".jpg", frame)
                if ok: samples.append(analyze_image_bytes(encoded.tobytes()))
            frame_idx += 1
        cap.release()
        if not samples:
            raise HTTPException(status_code=400, detail="No readable frames found.")
        avg = round(sum(x["vehicle_count"] for x in samples) / len(samples))
        peak = max(x["vehicle_count"] for x in samples)
        return {"sampled_frames": len(samples), "duration_seconds": duration,
                "average_vehicles_per_frame": avg, "peak_vehicles": peak,
                "density": "Low" if avg < 8 else "Medium" if avg < 20 else "High",
                "counts": {k: sum(x["counts"][k] for x in samples) for k in samples[0]["counts"]}}
    finally:
        if tmp_path and os.path.exists(tmp_path): os.remove(tmp_path)


# ==========================================
# ADAPTIVE TRAFFIC SIGNAL MANAGEMENT
# ==========================================

class TrafficInput(BaseModel):
    north: int = Field(default=0, ge=0, le=200)
    south: int = Field(default=0, ge=0, le=200)
    east: int = Field(default=0, ge=0, le=200)
    west: int = Field(default=0, ge=0, le=200)


@app.post("/api/adaptive-signal")
def adaptive_signal(data: TrafficInput):

    # Calculate traffic demand for each signal phase
    ns_demand = data.north + data.south
    ew_demand = data.east + data.west

    total_demand = ns_demand + ew_demand

    # Total green time available in one cycle
    total_green = 70
    minimum_green = 20

    # Calculate adaptive green timings
    if total_demand == 0:
        ns_green = 35
        ew_green = 35
        explanation = "No vehicles detected. Equal signal timing assigned."

    else:
        remaining = total_green - (2 * minimum_green)

        ns_green = minimum_green + round(
            remaining * ns_demand / total_demand
        )

        ew_green = total_green - ns_green

        explanation = (
            "Green time is allocated according to the "
            "relative traffic demand at the intersection."
        )

    # Classify congestion
    if total_demand < 15:
        congestion = "Low"
    elif total_demand < 40:
        congestion = "Medium"
    else:
        congestion = "High"

    return {
        "intersection": "Four-Way Intersection",
        "traffic": {
            "north": data.north,
            "south": data.south,
            "east": data.east,
            "west": data.west
        },
        "demand": {
            "north_south": ns_demand,
            "east_west": ew_demand,
            "total": total_demand
        },
        "congestion_level": congestion,
        "signal_recommendations": {
            "north_south": {
                "green_seconds": ns_green,
                "status": "GREEN"
            },
            "east_west": {
                "green_seconds": ew_green,
                "status": "GREEN"
            }
        },
        "yellow_seconds": 5,
        "explanation": explanation,
        "cycle_green_seconds": total_green
    }


