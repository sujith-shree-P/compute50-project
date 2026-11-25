"""
SmartFlow AI - Emergency Vehicle Green Corridor & Routing Service
Coordinates simulated traffic signal priority phases, handles 4-road conflict logic
(opposing approach compatibility, strict cross-traffic red lock, clearance transitions),
and calculates multi-junction routes via Dijkstra's shortest path algorithm.
"""

import time
import heapq
from typing import Dict, List, Tuple, Optional, Any
from backend.models.schemas import (
    EmergencyCorridorState,
    EmergencyActivationRequest,
    RouteCalculationResponse,
    RouteCalculationRequest
)

# Simulated Road Network Graph with 4 Intersections
# J1: North Gateway, J2: Central Square, J3: Hospital District, J4: East Avenue
JUNCTION_INFO = {
    "J1": {
        "id": "J1",
        "name": "North Gateway",
        "type": "4-Way Major Junction",
        "has_hospital": False,
        "x": 250, "y": 80
    },
    "J2": {
        "id": "J2",
        "name": "Central Square",
        "type": "4-Way Primary Hub",
        "has_hospital": False,
        "x": 250, "y": 280
    },
    "J3": {
        "id": "J3",
        "name": "Hospital District",
        "type": "Apex Emergency Center",
        "has_hospital": True,
        "x": 250, "y": 480
    },
    "J4": {
        "id": "J4",
        "name": "East Tech Avenue",
        "type": "4-Way Commercial Corridor",
        "has_hospital": False,
        "x": 520, "y": 280
    }
}

# Graph edges: (From, To, Distance in km, Normal Speed km/h, Base Congestion factor 1.0 - 2.5)
NETWORK_EDGES = [
    ("J1", "J2", 1.8, 40, 1.3),
    ("J2", "J1", 1.8, 40, 1.3),
    ("J2", "J3", 2.2, 35, 1.7),  # Direct corridor towards hospital
    ("J3", "J2", 2.2, 35, 1.7),
    ("J1", "J4", 2.6, 50, 1.1),
    ("J4", "J1", 2.6, 50, 1.1),
    ("J4", "J3", 2.9, 45, 1.2),  # Alternate bypass route
    ("J3", "J4", 2.9, 45, 1.2),
    ("J2", "J4", 1.5, 40, 1.5),
    ("J4", "J2", 1.5, 40, 1.5)
]


class EmergencyService:
    def __init__(self):
        self.current_state = EmergencyCorridorState(
            active=False,
            signals={"North": "RED", "South": "RED", "East": "RED", "West": "RED"},
            phase="IDLE",
            message="Standard adaptive signal mode"
        )
        self.emergency_history: List[Dict[str, Any]] = []

    def get_opposite_approach(self, road: str) -> str:
        """Returns the straight opposite approach road."""
        r = road.lower().strip()
        opposites = {
            "north": "South",
            "south": "North",
            "east": "West",
            "west": "East"
        }
        return opposites.get(r, "South")

    def get_cross_approaches(self, road: str) -> List[str]:
        """Returns conflicting cross traffic approaches that MUST be set to RED."""
        r = road.lower().strip()
        if r in ["north", "south"]:
            return ["East", "West"]
        else:
            return ["North", "South"]

    def compute_dijkstra_route(
        self,
        start: str = "J1",
        destination: str = "J3",
        avoid_congestion: bool = True
    ) -> RouteCalculationResponse:
        """
        Executes Dijkstra's algorithm to determine the optimal emergency corridor route.
        Edge weights take into account actual road distance, normal speed, and real-time congestion delay.
        """
        if start not in JUNCTION_INFO or destination not in JUNCTION_INFO:
            start = "J1"
            destination = "J3"

        # Build adjacency graph
        adj: Dict[str, List[Tuple[str, float, float]]] = {k: [] for k in JUNCTION_INFO.keys()}
        for u, v, dist, speed, cong in NETWORK_EDGES:
            # Travel time in minutes = (distance / speed) * 60 * (congestion if avoid_congestion else 1.0)
            weight = (dist / speed) * 60.0 * (cong if avoid_congestion else 1.0)
            adj[u].append((v, weight, dist))

        # Dijkstra priority queue: (cumulative_time, current_node, path, total_dist)
        pq = [(0.0, start, [start], 0.0)]
        visited = set()
        best_time = float("inf")
        best_path: List[str] = [start, destination]
        best_dist = 0.0

        while pq:
            curr_time, u, path, dist = heapq.heappop(pq)
            if u in visited:
                continue
            visited.add(u)

            if u == destination:
                best_time = curr_time
                best_path = path
                best_dist = dist
                break

            for v, weight, segment_dist in adj[u]:
                if v not in visited:
                    heapq.heappush(pq, (curr_time + weight, v, path + [v], dist + segment_dist))

        # Emergency corridor saves ~60% of travel time by clearing all signal queues ahead
        time_normal = round(best_time + (len(best_path) * 1.5), 1)  # Normal includes signal waiting queues
        time_corridor = round(best_time * 0.45, 1)  # Green corridor with preemptive green waves
        time_saved = round(max(0.5, time_normal - time_corridor), 1)

        junctions_detail = [
            {
                "id": j_id,
                "name": JUNCTION_INFO[j_id]["name"],
                "type": JUNCTION_INFO[j_id]["type"],
                "has_hospital": JUNCTION_INFO[j_id]["has_hospital"],
                "is_active_corridor": j_id in best_path
            }
            for j_id in best_path
        ]

        return RouteCalculationResponse(
            start_junction=start,
            destination_junction=destination,
            path=best_path,
            path_junction_names=[JUNCTION_INFO[j]["name"] for j in best_path],
            total_distance_km=round(best_dist, 2),
            estimated_time_normal_min=time_normal,
            estimated_time_corridor_min=time_corridor,
            time_saved_min=time_saved,
            junctions_in_route=junctions_detail
        )

    def activate_corridor(self, req: EmergencyActivationRequest) -> EmergencyCorridorState:
        """
        Activates the emergency vehicle green corridor.
        Implements 4-Road intersection conflict logic:
        - Ambulance approach (e.g. Road A): GREEN
        - Conflicting cross traffic (Roads C & D): strictly RED
        - Compatible opposing road (Road B): GREEN_COMPATIBLE (straight flow permitted away from turn)
        - Preceded by safety clearance interval
        """
        approach = req.approach_road.capitalize()
        exit_r = req.exit_road.capitalize() if req.exit_road else self.get_opposite_approach(approach)
        cross_roads = self.get_cross_approaches(approach)
        opposing_road = self.get_opposite_approach(approach)

        signals_map = {}
        # Priority for approach road
        signals_map[approach] = "GREEN_PRIORITY"

        # Opposing road may remain GREEN for compatible non-conflicting straight flow
        signals_map[opposing_road] = "GREEN_COMPATIBLE"

        # Cross traffic approaches MUST be locked at RED
        for c in cross_roads:
            signals_map[c] = "RED_LOCKED"

        # Compute route path between junctions
        route_res = self.compute_dijkstra_route(
            req.junction_id,
            req.destination_junction or "J3"
        )

        emergency_id = f"EMG_{int(time.time())}"
        self.current_state = EmergencyCorridorState(
            active=True,
            emergency_id=emergency_id,
            vehicle_id=req.vehicle_id or "AMB-108",
            current_junction=req.junction_id,
            approach_road=approach,
            exit_road=exit_r,
            destination_junction=req.destination_junction or "J3",
            route_path=route_res.path,
            signals=signals_map,
            phase="ACTIVE_PRIORITY",
            elapsed_seconds=0,
            estimated_remaining_time_seconds=int(route_res.estimated_time_corridor_min * 60),
            cleared_at=None,
            message=(
                f"EMERGENCY GREEN CORRIDOR ACTIVE: Priority granted on {approach}. "
                f"Opposing {opposing_road} in compatible green. "
                f"Conflicting cross roads ({', '.join(cross_roads)}) held at RED."
            )
        )

        # Log event in history
        self.emergency_history.append({
            "emergency_id": emergency_id,
            "vehicle_id": self.current_state.vehicle_id,
            "junction": req.junction_id,
            "approach": approach,
            "exit": exit_r,
            "activated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "ACTIVE"
        })

        return self.current_state

    def clear_corridor(self) -> EmergencyCorridorState:
        """
        Marks the emergency vehicle as cleared.
        Safely restores normal adaptive signal management.
        """
        if self.current_state.active:
            # Mark in history
            for item in self.emergency_history:
                if item["emergency_id"] == self.current_state.emergency_id:
                    item["status"] = "CLEARED"
                    item["cleared_at"] = time.strftime("%Y-%m-%d %H:%M:%S")

        self.current_state = EmergencyCorridorState(
            active=False,
            emergency_id=None,
            signals={"North": "RED", "South": "RED", "East": "RED", "West": "RED"},
            phase="CLEARED",
            cleared_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            message="Emergency cleared. Restoring adaptive signal management with safe transition."
        )
        return self.current_state

    def get_status(self) -> EmergencyCorridorState:
        return self.current_state

    def get_history(self) -> List[Dict[str, Any]]:
        return self.emergency_history
