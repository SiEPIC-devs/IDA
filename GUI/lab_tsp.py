import json
import math
import os
import time
from pathlib import Path
import matplotlib.pyplot as plt
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import matplotlib


class TSPSolver:

    def __init__(
        self,
        coord_json: str,
        selected_json: str,
        time_limit: int = 10,
        output_dir: str = "./res",
    ):

        self.coord_json   = Path(coord_json)
        self.selected_json = Path(selected_json)
        self.time_limit    = time_limit
        self.output_dir    = Path(output_dir)

        self.numbers = [0]
        self.points  = [(0, 0)]
        self.selected_numbers = []

        self._load_selected_numbers()
        self._load_coordinates()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def solve_and_plot(self) -> None:
        self._build_distance_matrix()
        solution = self._solve_tsp()

        if solution is None:
            print("⚠️  No Path")

        xs, ys, total_dist = self._print_solution(solution)

        ts = int(time.time() * 1000)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        latest_png = self.output_dir / f"tsp_result_{ts}.png"

        self._plot_route(xs, ys, latest_png)
        self._cleanup_old_plots(keep=1)          # 只留最新一张

        print(f"\n📸 Saved in path: {latest_png.resolve()}")
        self.path = f"tsp_result_{ts}.png"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_selected_numbers(self) -> None:
        with self.selected_json.open("r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                self.selected_numbers = set(data.get("Selection", []))
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON: {e}")
                self.selected_numbers = set()

    def _load_coordinates(self) -> None:
        with self.coord_json.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        for v in raw["_default"].values():
            num = v["number"]
            if num in self.selected_numbers:
                self.numbers.append(num)
                self.points.append(tuple(v["coordinate"][:2]))

        if len(self.numbers) == 1:
            raise ValueError("⚠️  Do Not Have Any Devices")

    def _build_distance_matrix(self) -> None:
        self.dist = [
            [int(math.hypot(x1 - x2, y1 - y2)) for x2, y2 in self.points]
            for x1, y1 in self.points
        ]

    def _solve_tsp(self):
        N = len(self.points)
        mgr = pywrapcp.RoutingIndexManager(N, 1, 0)
        routing = pywrapcp.RoutingModel(mgr)

        cb = routing.RegisterTransitCallback(
            lambda i, j: self.dist[mgr.IndexToNode(i)][mgr.IndexToNode(j)]
        )
        routing.SetArcCostEvaluatorOfAllVehicles(cb)

        params = pywrapcp.DefaultRoutingSearchParameters()
        params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        params.time_limit.seconds = self.time_limit

        return routing.SolveWithParameters(params), routing, mgr

    def _print_solution(self, solve_tuple):
        solution, routing, mgr = solve_tuple
        idx = routing.Start(0)
        step = 0
        total_dist = 0
        xs, ys = [], []
        self.route_idx = []

        print(f"{'Step':>4} {'Device':>8} {'X':>10} {'Y':>10}")
        while not routing.IsEnd(idx):
            nid = mgr.IndexToNode(idx)
            x, y = self.points[nid]
            print(f"{step:>4} {self.numbers[nid]:>8} {x:>10} {y:>10}")

            xs.append(x)
            ys.append(y)
            self.route_idx.append(self.numbers[nid] - 1)

            next_idx = solution.Value(routing.NextVar(idx))
            total_dist += self.dist[nid][mgr.IndexToNode(next_idx)]
            idx = next_idx
            step += 1

        xs.append(0)
        ys.append(0)
        print(f"{step:>4} {0:>8} {0:>10} {0:>10}  ← Return to Origin")
        print(f"\nTotal Distance ≈ {total_dist} (same unit as coordinates)")
        return xs, ys, total_dist

    def _plot_route(self, xs, ys, png_path: Path) -> None:
        matplotlib.use("Agg")
        plt.figure(figsize=(8, 8))
        plt.plot(xs, ys, '-o', markersize=3, linewidth=1)
        plt.title("TSP Route")
        plt.gca().set_aspect('equal', adjustable='box')
        plt.grid(True, linestyle='--', alpha=0.3)
        plt.savefig(png_path, dpi=300, bbox_inches='tight', pad_inches=0.05)
        plt.close()

    def _cleanup_old_plots(self, keep: int = 1) -> None:
        files = sorted(
            (p for p in self.output_dir.glob("tsp_result_*.png")),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        for p in files[keep:]:
            try:
                p.unlink()
            except OSError:
                pass
