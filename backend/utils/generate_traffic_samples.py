"""
SmartFlow AI - Sample Traffic Image Generator
Creates realistic visual test images containing recognizable vehicles and roads
for instant end-to-end testing of 1-road, 2-road, 4-road, combined 4-way intersection,
and ambulance emergency scenarios.
"""

import os
import cv2
import numpy as np


def draw_vehicle(img, x, y, w, h, vtype="car", color=(40, 100, 200)):
    """Draws a recognizable stylized top-down or perspective vehicle."""
    # Body
    cv2.rectangle(img, (x, y), (x + w, y + h), color, -1)
    cv2.rectangle(img, (x, y), (x + w, y + h), (20, 20, 20), 2)
    # Windshields
    if vtype == "car":
        cv2.rectangle(img, (x + 4, y + int(h * 0.2)), (x + w - 4, y + int(h * 0.4)), (180, 220, 240), -1)
        cv2.rectangle(img, (x + 4, y + int(h * 0.65)), (x + w - 4, y + int(h * 0.8)), (180, 220, 240), -1)
        # Roof
        cv2.rectangle(img, (x + 6, y + int(h * 0.38)), (x + w - 6, y + int(h * 0.67)), color, -1)
    elif vtype == "bus":
        cv2.rectangle(img, (x + 4, y + 6), (x + w - 4, y + 16), (200, 240, 255), -1)
        for wy in range(y + 24, y + h - 15, 14):
            cv2.rectangle(img, (x + 2, wy), (x + 7, wy + 8), (200, 240, 255), -1)
            cv2.rectangle(img, (x + w - 7, wy), (x + w - 2, wy + 8), (200, 240, 255), -1)
    elif vtype == "truck":
        # Cabin
        cv2.rectangle(img, (x, y), (x + w, y + int(h * 0.35)), color, -1)
        # Cargo container
        cv2.rectangle(img, (x - 2, y + int(h * 0.38)), (x + w + 2, y + h), (90, 90, 100), -1)
    elif vtype == "ambulance":
        # White body with red cross
        cv2.rectangle(img, (x, y), (x + w, y + h), (250, 250, 250), -1)
        cv2.rectangle(img, (x, y), (x + w, y + h), (20, 20, 20), 2)
        # Red emergency cross
        cx, cy = x + w // 2, y + h // 2
        cv2.rectangle(img, (cx - 4, cy - 14), (cx + 4, cy + 14), (0, 0, 220), -1)
        cv2.rectangle(img, (cx - 14, cy - 4), (cx + 14, cy + 4), (0, 0, 220), -1)
        # Flashing siren lights (red & blue)
        cv2.circle(img, (x + 8, y + 6), 4, (0, 0, 255), -1)
        cv2.circle(img, (x + w - 8, y + 6), 4, (255, 100, 0), -1)


def generate_all_samples(out_dir: str = "public/sample_images"):
    os.makedirs(out_dir, exist_ok=True)

    # 1. Road North: Heavy traffic
    img_n = np.full((480, 640, 3), (70, 75, 80), dtype=np.uint8)  # Asphalt
    cv2.line(img_n, (320, 0), (320, 480), (255, 255, 255), 2)     # Lane divider
    draw_vehicle(img_n, 200, 40, 45, 80, "car", (30, 80, 190))
    draw_vehicle(img_n, 200, 150, 45, 80, "car", (180, 40, 30))
    draw_vehicle(img_n, 200, 260, 55, 120, "bus", (30, 140, 40))
    draw_vehicle(img_n, 200, 400, 45, 75, "car", (220, 180, 20))
    draw_vehicle(img_n, 380, 60, 50, 110, "truck", (120, 70, 40))
    draw_vehicle(img_n, 380, 200, 45, 80, "car", (190, 190, 190))
    draw_vehicle(img_n, 380, 310, 45, 80, "car", (40, 40, 40))
    cv2.imwrite(os.path.join(out_dir, "north_road.jpg"), img_n)

    # 2. Road South: Moderate traffic
    img_s = np.full((480, 640, 3), (70, 75, 80), dtype=np.uint8)
    cv2.line(img_s, (320, 0), (320, 480), (255, 255, 255), 2)
    draw_vehicle(img_s, 220, 100, 45, 80, "car", (210, 40, 40))
    draw_vehicle(img_s, 220, 240, 45, 80, "car", (50, 180, 50))
    draw_vehicle(img_s, 370, 180, 50, 105, "truck", (60, 60, 160))
    cv2.imwrite(os.path.join(out_dir, "south_road.jpg"), img_s)

    # 3. Road East: Congested traffic
    img_e = np.full((480, 640, 3), (70, 75, 80), dtype=np.uint8)
    cv2.line(img_e, (320, 0), (320, 480), (255, 255, 255), 2)
    draw_vehicle(img_e, 190, 20, 55, 125, "bus", (30, 140, 40))
    draw_vehicle(img_e, 195, 160, 45, 80, "car", (170, 170, 30))
    draw_vehicle(img_e, 195, 260, 45, 80, "car", (140, 30, 150))
    draw_vehicle(img_e, 195, 360, 45, 80, "car", (30, 120, 210))
    draw_vehicle(img_e, 370, 30, 50, 115, "truck", (110, 80, 40))
    draw_vehicle(img_e, 375, 170, 45, 80, "car", (20, 20, 20))
    draw_vehicle(img_e, 375, 270, 45, 80, "car", (200, 200, 200))
    draw_vehicle(img_e, 375, 370, 45, 80, "car", (200, 50, 50))
    cv2.imwrite(os.path.join(out_dir, "east_road.jpg"), img_e)

    # 4. Road West: Light traffic
    img_w = np.full((480, 640, 3), (70, 75, 80), dtype=np.uint8)
    cv2.line(img_w, (320, 0), (320, 480), (255, 255, 255), 2)
    draw_vehicle(img_w, 230, 140, 45, 80, "car", (50, 130, 220))
    cv2.imwrite(os.path.join(out_dir, "west_road.jpg"), img_w)

    # 5. Combined 4-Way Intersection
    img_4w = np.full((640, 640, 3), (55, 120, 60), dtype=np.uint8)  # Grass background
    # Vertical Road (North-South)
    cv2.rectangle(img_4w, (220, 0), (420, 640), (70, 75, 80), -1)
    # Horizontal Road (East-West)
    cv2.rectangle(img_4w, (0, 220), (640, 420), (70, 75, 80), -1)
    # Center junction box
    cv2.rectangle(img_4w, (220, 220), (420, 420), (80, 85, 90), -1)
    # Road markings
    cv2.line(img_4w, (320, 0), (320, 220), (255, 255, 255), 2)
    cv2.line(img_4w, (320, 420), (320, 640), (255, 255, 255), 2)
    cv2.line(img_4w, (0, 320), (220, 320), (255, 255, 255), 2)
    cv2.line(img_4w, (420, 320), (640, 320), (255, 255, 255), 2)

    # North approach vehicles
    draw_vehicle(img_4w, 240, 40, 35, 65, "car", (40, 100, 210))
    draw_vehicle(img_4w, 240, 120, 40, 85, "bus", (30, 140, 40))
    draw_vehicle(img_4w, 345, 70, 40, 75, "car", (210, 40, 40))

    # South approach vehicles
    draw_vehicle(img_4w, 245, 460, 35, 65, "car", (180, 180, 30))
    draw_vehicle(img_4w, 345, 520, 40, 80, "truck", (120, 70, 40))

    # East approach vehicles (horizontal)
    draw_vehicle(img_4w, 460, 240, 65, 35, "car", (190, 40, 180))
    draw_vehicle(img_4w, 540, 240, 65, 35, "car", (30, 180, 200))
    draw_vehicle(img_4w, 480, 345, 80, 40, "bus", (40, 150, 40))

    # West approach vehicles (horizontal)
    draw_vehicle(img_4w, 90, 345, 65, 35, "car", (210, 210, 210))

    cv2.imwrite(os.path.join(out_dir, "combined_intersection.jpg"), img_4w)

    # 6. Ambulance Sample Image
    img_amb = np.full((480, 640, 3), (70, 75, 80), dtype=np.uint8)
    cv2.line(img_amb, (320, 0), (320, 480), (255, 255, 255), 2)
    # Draw large emergency ambulance
    draw_vehicle(img_amb, 270, 160, 100, 180, "ambulance")
    cv2.putText(img_amb, "AMBULANCE", (275, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 220), 2)
    cv2.imwrite(os.path.join(out_dir, "ambulance_sample.jpg"), img_amb)

    print(f"[Samples] Successfully generated sample traffic images in {out_dir}")


if __name__ == "__main__":
    generate_all_samples()
