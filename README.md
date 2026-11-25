# SmartFlow AI

> **AI-Powered Dynamic Intersection Congestion Resolution & Emergency Vehicle Green Corridor Management System**

![SmartFlow AI Status](https://img.shields.io/badge/Status-Functional%20Prototype-emerald)
![Python](https://img.shields.io/badge/Python-3.10%2B%20%7C%203.14%2B-blue)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-teal)
![Computer Vision](https://img.shields.io/badge/AI-YOLOv8%20%7C%20OpenCV-orange)
![Frontend](https://img.shields.io/badge/Frontend-React%20%7C%20TailwindCSS%20%7C%20Chart.js-indigo)
![License](https://img.shields.io/badge/License-AGPL--3.0-purple)

---

## 🚦 Executive Summary

Conventional urban traffic systems rely on fixed, timer-based signal controllers. This introduces severe city-wide inefficiencies:
1. **Intersection Congestion**: Unbalanced traffic surges cause gridlocks where heavily packed roads wait on fixed red lights while empty lanes enjoy idle green time.
2. **Emergency Vehicle Delays**: Ambulances and first-responders are delayed at intersections, increasing hospital transit times and risking critical patient lives.

**SmartFlow AI** provides a complete, modern, software-based solution uniting **AI-Powered Dynamic Signal Timing** with a **Preemptive Emergency Vehicle Green Corridor**. The platform processes actual uploaded images via genuine **Ultralytics YOLOv8** computer vision inference, computes Passenger Car Unit (PCU) congestion scores, dynamically shifts green durations, and orchestrates multi-junction green waves via **Dijkstra's shortest path algorithm**.

---

## 📋 Table of Contents

- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [How Vehicle Detection Works](#-how-vehicle-detection-works)
- [Adaptive Signal Timing Algorithm](#-adaptive-signal-timing-algorithm)
- [Emergency Green Corridor Management](#-emergency-green-corridor-management)
- [Technology Stack](#-technology-stack)
- [Project Directory Structure](#-project-directory-structure)
- [Installation & Quick Start](#-installation--quick-start)
- [API Reference](#-api-reference)
- [Verification & Automated Tests](#-verification--automated-tests)
- [Known Limitations & Prototype Scope](#-known-limitations--prototype-scope)
- [Third-Party Attribution & Licensing](#-third-party-attribution--licensing)

---

## 🌟 Key Features

### Module 1: Adaptive Traffic Signal Management
- **Flexible Image Uploads**: Supports single road approach, two-road intersections, four separate directional approaches (North, South, East, West), or a single combined 4-way intersection image.
- **Spatial Quadrant Zoning**: Automatic or configurable quadrant partitioning for combined intersection photos, ensuring vehicles are attributed to the correct directional approach.
- **Genuine YOLOv8 Object Detection**: Detects and categorizes vehicles into **Cars**, **Motorcycles**, **Buses**, and **Trucks** with bounding boxes, confidence scores, and count tables.
- **Passenger Car Unit (PCU) Weighting**: Translates heterogeneous traffic (buses, heavy trucks, two-wheelers) into standardized PCU scores based on Indian Road Congress (IRC) traffic engineering standards.
- **Webster-Inspired Dynamic Timing**: Proportional allocation of green clearance time bound between configurable minimum (15s) and maximum (60s) constraints, with mandatory yellow transitions (3s) and all-red clearance intervals (2s).
- **Manual Audit & Correction**: Allows traffic operators to manually correct detected counts for edge cases while clearly logging the adjustment.

### Module 2: Emergency Vehicle Green Corridor Management
- **Ambulance AI Verification & Human-in-the-Loop Confirmation**: Verifies vehicle geometry with emergency livery detection, pairing automated recognition with 1-click confirmation before overriding municipal signals.
- **4-Road Intersection Conflict Logic**:
  - **Approach Road A**: Receives preemptive **GREEN**.
  - **Cross-Traffic C & D**: Locked strictly at **RED**.
  - **Opposing Approach B**: Permitted **Compatible GREEN** for non-conflicting straight flow away from the ambulance lane.
- **Multi-Junction Dijkstra Routing**: Computes the optimal emergency transit corridor between simulated network junctions (J1 North Gateway, J2 Central Square, J3 Hospital District, J4 East Tech Avenue) based on distance, posted speed, and real-time congestion weights.
- **Safe State Transitions**: Enforces yellow clearance and all-red intervals before establishing the green corridor, and restores normal adaptive cycles upon marking the ambulance as cleared.

### Visual Simulation & Analytics
- **Interactive 2D Junction Canvas**: Real-time visualization of a 4-way junction with glowing tri-color signal heads, countdown timers, approach queues, and animated ambulance corridor clearance.
- **Chart.js Performance Analytics**:
  1. *Fixed vs Adaptive Timing comparison bar chart*
  2. *Ambulance Delay comparison bar chart (Normal vs Green Corridor)*
  3. *Vehicle Volume distribution by road*
  4. *Simulated Queue Stabilization over consecutive signal cycles*

---

## 🏗️ System Architecture

```mermaid
graph TD
    UI["Frontend Dashboard (React + Tailwind + Chart.js)"]
    API["FastAPI Core Router (/api)"]
    
    subgraph "Computer Vision Pipeline"
        YOLO["Ultralytics YOLOv8 Inference Engine"]
        CV["OpenCV Annotator & Quadrant Partitioner"]
        PCU["PCU Traffic Density Analyzer"]
    end
    
    subgraph "Traffic Engineering & Control"
        SIG["Adaptive Signal Timing Service"]
        EMG["Emergency Corridor Conflict Coordinator"]
        DIJK["Dijkstra Multi-Junction Router"]
    end
    
    UI -->|Image Upload & Parameters| API
    API --> YOLO
    YOLO --> CV
    CV --> PCU
    PCU --> SIG
    SIG -->|Dynamic Green Allocations| UI
    
    UI -->|Ambulance Verification & Route| EMG
    EMG --> DIJK
    EMG -->|4-Road Conflict Matrix (A Green, B Compatible, C&D Red)| UI
```

---

## 👁️ How Vehicle Detection Works

1. **Image Preprocessing**: Uploaded image bytes are decoded via OpenCV into BGR matrices without saving temporary files to disk.
2. **YOLOv8n Inference**: The model evaluates bounding boxes and classification probabilities using the official COCO-trained weights (`yolov8n.pt`).
3. **Class Filtering**:
   - Class 2: `cars` (Weight: 1.0 PCU)
   - Class 3: `motorcycles` (Weight: 0.5 PCU)
   - Class 5: `buses` (Weight: 2.2 PCU)
   - Class 7: `trucks` (Weight: 2.5 PCU)
4. **Spatial Partitioning (Combined Images)**:
   - For combined intersection photos, the image is partitioned into geometric quadrants (North, South, East, West). Detected bounding box centers are assigned to their respective approach.
5. **Annotation**: Crisp color-coded bounding boxes, category labels, confidence scores, and an informational summary header are rendered via OpenCV and delivered to the frontend as base64 JPEG strings.

---

## ⏱️ Adaptive Signal Timing Algorithm

Standard fixed signals allocate an arbitrary static green duration (e.g., 30s per approach). SmartFlow AI computes adaptive green time using a proportional demand formula:

$$\text{PCU}_i = 1.0 \times \text{Cars}_i + 0.5 \times \text{Bikes}_i + 2.2 \times \text{Buses}_i + 2.5 \times \text{Trucks}_i$$

$$\text{Green}_i = \text{clamp}\left(\frac{\text{PCU}_i}{\sum_{j} \text{PCU}_j} \times T_{\text{available}}, G_{\min}, G_{\max}\right)$$

Where:
- $G_{\min} = 15\text{s}$ (Minimum pedestrian / clearance green)
- $G_{\max} = 60\text{s}$ (Maximum green cap to prevent starve-out of cross approaches)
- Yellow transition interval: $3\text{s}$
- All-red clearance interval: $2\text{s}$

---

## 🚑 Emergency Green Corridor Management

### 4-Approach Intersection Conflict Matrix
When an ambulance approaches from **Road A** heading towards **Road B**:
- **Road A (Approach)**: `GREEN_PRIORITY`
- **Road B (Opposite)**: `GREEN_COMPATIBLE` (allowed for non-conflicting straight flow)
- **Road C & D (Cross)**: `RED_LOCKED` (strict safety lock)

Before entering priority mode, an all-red clearance interval clears active vehicles inside the intersection box. The priority mode remains locked until the operator clicks **"Mark Ambulance as Cleared"**, restoring safe adaptive cycles.

### Multi-Junction Dijkstra Routing
A simulated road graph maps 4 key junctions:
- **J1 (North Gateway)**
- **J2 (Central Square Hub)**
- **J3 (Hospital District - Apex Emergency Center)**
- **J4 (East Tech Avenue)**

Edge weights model real travel impedance:
$$\text{Cost}_{u,v} = \frac{\text{Distance}_{u,v}}{\text{Speed}_{u,v}} \times 60 \times \text{CongestionFactor}_{u,v}$$

Dijkstra's algorithm selects the fastest route and preemptively clears signals downstream before the ambulance arrives.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, Tailwind CSS, Chart.js 4, Lucide Icons, Babel Standalone |
| **Backend** | Python 3.10+ / 3.14+, FastAPI, Uvicorn, Pydantic v2 |
| **AI & CV** | Ultralytics YOLOv8, PyTorch, OpenCV, Pillow, NumPy |
| **Algorithms** | Webster Proportional Allocation, Dijkstra Shortest Path, IRC PCU Index |
| **Testing** | Pytest, FastAPI TestClient, HTTPX |

---

## 📁 Project Directory Structure

```text
SmartFlow-AI/
├── backend/
│   ├── main.py                     # Main FastAPI application entrypoint
│   ├── models/
│   │   ├── schemas.py              # Pydantic data schemas
│   │   └── yolov8n.pt              # YOLOv8 nano model weights
│   ├── routes/
│   │   ├── detection.py            # Image upload & YOLO detection endpoints
│   │   ├── signals.py              # Adaptive timing calculation endpoints
│   │   ├── emergency.py            # Green corridor & Dijkstra route endpoints
│   │   └── analytics.py            # KPI & history aggregation endpoints
│   ├── services/
│   │   ├── detector_service.py     # Genuine YOLOv8 inference & OpenCV annotation
│   │   ├── signal_service.py       # Webster/PCU adaptive timing algorithm
│   │   └── emergency_service.py    # 4-road conflict matrix & Dijkstra router
│   ├── utils/
│   │   └── generate_traffic_samples.py # Pre-generated test image generator
│   └── tests/
│       └── test_api.py             # Complete automated test suite (TEST 1 - 11)
├── frontend/
│   ├── index.html                  # Responsive SPA host template
│   └── src/
│       └── app.jsx                 # Full React application (7 core sections)
├── public/
│   └── sample_images/              # Preloaded sample traffic photos for testing
├── docs/                           # Architecture and design documentation
├── package.json                    # Node.js project manifest & scripts
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
├── .gitignore                      # Git exclusion rules
├── LICENSE                         # AGPL-3.0 License
└── README.md                       # Comprehensive project documentation
```

---

## 🚀 Installation & Quick Start

### 1. Prerequisites
- Python 3.10 or higher
- Git (optional, for cloning)

### 2. Setup Virtual Environment & Install Dependencies
```bash
# Clone the repository
git clone https://github.com/<your-username>/SmartFlow-AI.git
cd SmartFlow-AI

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Verify or Download YOLO Model Weights
If `backend/models/yolov8n.pt` is not present, download it using curl or Python:
```bash
curl -k -L -o backend/models/yolov8n.pt "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n.pt"
```

### 4. Run Pre-generated Test Image Generator (Optional)
To generate fresh test photos in `public/sample_images/`:
```bash
python backend/utils/generate_traffic_samples.py
```

### 5. Launch Application Server
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser and navigate to:
👉 **`http://localhost:8000/`** (Interactive Web Dashboard)  
👉 **`http://localhost:8000/docs`** (Interactive OpenAPI / Swagger Documentation)

---

## 📡 API Reference

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/api/health` | `GET` | Health check confirming YOLO model and backend state |
| `/api/detect/single` | `POST` | Upload and analyze 1 road photograph |
| `/api/detect/multi` | `POST` | Upload up to 4 separate road photos (North, South, East, West) |
| `/api/detect/combined` | `POST` | Upload combined 4-way intersection photo with quadrant zoning |
| `/api/detect/ambulance` | `POST` | Upload ambulance image for AI verification |
| `/api/detect/manual-adjust` | `POST` | Correct a vehicle count with audit trail |
| `/api/signals/calculate` | `POST` | Calculate adaptive signal timings based on detected counts |
| `/api/emergency/activate` | `POST` | Trigger emergency green corridor (Road A priority, C&D red) |
| `/api/emergency/clear` | `POST` | Clear emergency priority and restore safe adaptive cycles |
| `/api/emergency/route` | `POST` | Compute optimal multi-junction route via Dijkstra |
| `/api/analytics/summary` | `GET` | Retrieve aggregate KPI analytics and performance metrics |

---

## 🧪 Verification & Automated Tests

Run the complete automated test suite verifying all required test cases (TEST 1 through TEST 11):
```bash
pytest backend/tests/test_api.py -v
```

### Automated Test Coverage:
- `test_health_check`: Confirms API and YOLO model availability.
- `test_1_single_road_detection`: Verifies single road upload produces genuine vehicle counts.
- `test_2_different_road_different_counts`: Verifies separate images produce independent results without count reuse.
- `test_3_multi_road_detection`: Verifies North, South, East, West multi-image analysis.
- `test_4_combined_intersection_detection`: Verifies combined intersection quadrant partitioning.
- `test_6_adaptive_signal_timing`: Verifies dynamic green time recalculation based on detected PCU volume.
- `test_7_8_emergency_corridor_conflict_logic`: Verifies Road A receives green, opposing B is compatible green, and cross roads C & D are locked at RED.
- `test_9_emergency_cleared`: Verifies safe termination and return to adaptive control.
- `test_10_analytics_summary`: Verifies metrics calculation and before-and-after reporting.
- `test_11_invalid_empty_uploads`: Verifies error handling for unsupported formats and zero-byte uploads.

---

## ⚠️ Known Limitations & Prototype Scope

1. **Hackathon Software Prototype**: This application is a software-based research and demonstration prototype. It does not interface directly with real municipal physical traffic light controllers or roadside CCTV hardware.
2. **COCO Vehicle Classes**: Standard pretrained COCO YOLO models recognize **Cars**, **Motorcycles**, **Buses**, and **Trucks**. Indian auto-rickshaws are typically categorized under small light vehicles/cars or motorcycles.
3. **Emergency Preemption Verification**: General COCO models do not include an isolated "ambulance" class. SmartFlow AI combines vehicle detection with emergency livery color recognition and provides an explicit **human-in-the-loop confirmation** step before preemption is engaged.
4. **Static Photograph vs Live Stream**: Analysis is performed on uploaded still images; queue lengths are calculated from the photograph's vehicle density and simulated across consecutive timing cycles.

---

## 📄 Third-Party Attribution & Licensing

- **License**: GNU Affero General Public License v3.0 ([AGPL-3.0](LICENSE)).
- **Ultralytics YOLOv8**: Developed by Ultralytics Inc. ([AGPL-3.0 License](https://github.com/ultralytics/ultralytics/blob/main/LICENSE)).
- **OpenCV**: Distributed under the [Apache-2.0 License](https://opencv.org/license/).
- **FastAPI**: Distributed under the [MIT License](https://fastapi.tiangolo.com/).
- **PyTorch**: Distributed under the [Modified BSD License](https://github.com/pytorch/pytorch/blob/main/LICENSE).
- **React & Tailwind CSS**: Distributed under the [MIT License](https://opensource.org/licenses/MIT).
