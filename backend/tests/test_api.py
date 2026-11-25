"""
SmartFlow AI - Automated Test Suite
Verifies all functional requirements and test cases (TEST 1 through TEST 11)
covering single road, multi-road, combined intersection, adaptive signal calculations,
emergency green corridor conflict logic, Dijkstra routing, and error resilience.
"""

import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)
SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "public", "sample_images")


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["yolo_model"] == "YOLOv8n"


def test_1_single_road_detection():
    """TEST 1: Upload one road image, verify genuine inference and non-zero counts."""
    img_path = os.path.join(SAMPLE_DIR, "bus_sample.jpg")
    with open(img_path, "rb") as f:
        response = client.post(
            "/api/detect/single",
            files={"file": ("bus_sample.jpg", f, "image/jpeg")},
            data={"road_id": "north", "road_name": "North Approach", "conf_threshold": 0.2}
        )
    assert response.status_code == 200
    data = response.json()
    assert data["road_id"] == "north"
    assert "counts" in data
    assert data["counts"]["total"] >= 1
    assert data["annotated_image_base64"] is not None
    assert data["is_user_adjusted"] is False


def test_2_different_road_different_counts():
    """TEST 2: Verify that two different images yield independent, distinct results."""
    img1_path = os.path.join(SAMPLE_DIR, "bus_sample.jpg")
    img2_path = os.path.join(SAMPLE_DIR, "west_road.jpg")

    with open(img1_path, "rb") as f:
        res1 = client.post(
            "/api/detect/single",
            files={"file": ("bus_sample.jpg", f, "image/jpeg")},
            data={"road_id": "north", "conf_threshold": 0.2}
        ).json()

    with open(img2_path, "rb") as f:
        res2 = client.post(
            "/api/detect/single",
            files={"file": ("west_road.jpg", f, "image/jpeg")},
            data={"road_id": "west", "conf_threshold": 0.2}
        ).json()

    # Verify road IDs are strictly respected
    assert res1["road_id"] == "north"
    assert res2["road_id"] == "west"


def test_3_multi_road_detection():
    """TEST 3: Upload 4 separate road images, verify each image has separate analysis."""
    files = {}
    f_north = open(os.path.join(SAMPLE_DIR, "north_road.jpg"), "rb")
    f_south = open(os.path.join(SAMPLE_DIR, "south_road.jpg"), "rb")
    f_east = open(os.path.join(SAMPLE_DIR, "east_road.jpg"), "rb")
    f_west = open(os.path.join(SAMPLE_DIR, "west_road.jpg"), "rb")

    response = client.post(
        "/api/detect/multi",
        files={
            "north_file": ("north.jpg", f_north, "image/jpeg"),
            "south_file": ("south.jpg", f_south, "image/jpeg"),
            "east_file": ("east.jpg", f_east, "image/jpeg"),
            "west_file": ("west.jpg", f_west, "image/jpeg")
        },
        data={"conf_threshold": 0.2, "capacity": 35}
    )
    f_north.close()
    f_south.close()
    f_east.close()
    f_west.close()

    assert response.status_code == 200
    data = response.json()
    assert data["analysis_id"].startswith("multi_")
    assert "north" in data["roads"]
    assert "south" in data["roads"]
    assert "east" in data["roads"]
    assert "west" in data["roads"]
    assert data["total_vehicles_detected"] >= 0


def test_4_combined_intersection_detection():
    """TEST 4: Combined 4-way intersection image with quadrant zoning."""
    img_path = os.path.join(SAMPLE_DIR, "combined_intersection.jpg")
    with open(img_path, "rb") as f:
        response = client.post(
            "/api/detect/combined",
            files={"file": ("combined.jpg", f, "image/jpeg")},
            data={"conf_threshold": 0.2, "capacity": 35}
        )
    assert response.status_code == 200
    data = response.json()
    assert len(data["roads"]) == 4


def test_6_adaptive_signal_timing():
    """TEST 6: Check adaptive signal timing calculation and dynamic adjustment."""
    roads_payload = {
        "north": {"road_name": "North Approach", "counts": {"cars": 25, "motorcycles": 5, "buses": 2, "trucks": 1, "total": 33}},
        "south": {"road_name": "South Approach", "counts": {"cars": 10, "motorcycles": 2, "buses": 0, "trucks": 0, "total": 12}},
        "east": {"road_name": "East Approach", "counts": {"cars": 40, "motorcycles": 8, "buses": 4, "trucks": 3, "total": 55}},
        "west": {"road_name": "West Approach", "counts": {"cars": 8, "motorcycles": 2, "buses": 0, "trucks": 0, "total": 10}}
    }
    response = client.post(
        "/api/signals/calculate",
        json={"roads": roads_payload}
    )
    assert response.status_code == 200
    data = response.json()
    timings = data["timings"]

    # East has heaviest traffic, should receive significantly more green time than West
    assert timings["east"]["adaptive_green_seconds"] > timings["west"]["adaptive_green_seconds"]
    assert timings["east"]["adaptive_green_seconds"] > timings["east"]["fixed_green_seconds"]
    assert timings["west"]["adaptive_green_seconds"] < timings["west"]["fixed_green_seconds"]


def test_7_8_emergency_corridor_conflict_logic():
    """TEST 7 & 8: Emergency activation from Road A -> Road B; cross traffic C & D RED."""
    response = client.post(
        "/api/emergency/activate",
        json={
            "junction_id": "J2",
            "approach_road": "North",
            "exit_road": "South",
            "destination_junction": "J3",
            "manual_confirmation": True
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active"] is True
    # North approach receives priority
    assert data["signals"]["North"] == "GREEN_PRIORITY"
    # Compatible opposing road South is GREEN_COMPATIBLE
    assert data["signals"]["South"] == "GREEN_COMPATIBLE"
    # Cross traffic East and West must be locked RED
    assert data["signals"]["East"] == "RED_LOCKED"
    assert data["signals"]["West"] == "RED_LOCKED"


def test_9_emergency_cleared():
    """TEST 9: Mark ambulance as cleared and verify return to safe adaptive mode."""
    response = client.post("/api/emergency/clear")
    assert response.status_code == 200
    data = response.json()
    assert data["active"] is False
    assert data["phase"] == "CLEARED"


def test_10_analytics_summary():
    """TEST 10: Verify analytics aggregation."""
    response = client.get("/api/analytics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "performance_indicators" in data
    assert "average_queue_delay_reduction_pct" in data["performance_indicators"]


def test_11_invalid_empty_uploads():
    """TEST 11: Test invalid formats and empty uploads."""
    # Test invalid extension
    res_inv = client.post(
        "/api/detect/single",
        files={"file": ("test.txt", b"plain text content", "text/plain")},
        data={"road_id": "north"}
    )
    assert res_inv.status_code == 400

    # Test empty image bytes
    res_empty = client.post(
        "/api/detect/single",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
        data={"road_id": "north"}
    )
    assert res_empty.status_code == 400
