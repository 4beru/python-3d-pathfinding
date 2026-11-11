"""Visualization-independent data for the four pathfinding examples.

Coordinates are node coordinates, without voxel-center shifts. Connected grids
have display offsets only: their underlying pathfinding coordinates stay intact.
Importing this module does not load maps or run any pathfinding.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from pathfinding3d.core.diagonal_movement import DiagonalMovement
from pathfinding3d.core.grid import Grid
from pathfinding3d.core.node import GridNode
from pathfinding3d.core.world import World
from pathfinding3d.finder.a_star import AStarFinder
from pathfinding3d.finder.theta_star import ThetaStarFinder


Point = tuple[float, float, float]


@dataclass
class SceneGrid:
    matrix: np.ndarray
    offset: Point


@dataclass
class Route:
    name: str
    points: list[Point]
    cost: float
    runs: int
    color: tuple[float, float, float]


@dataclass
class Scenario:
    name: str
    title: str
    grids: list[SceneGrid]
    routes: list[Route]
    start: Point
    end: Point
    connections: list[tuple[Point, Point]]


SCENARIOS: dict[str, str] = {
    "basic": "A* on a 3 x 3 x 3 grid with a central obstacle",
    "connected": "A* across two grids connected by a bidirectional bridge",
    "sample": "A* through the bundled sample map",
    "theta": "Theta* versus A* on a 10 x 10 x 10 grid",
}

_RED = (1.0, 0.0, 0.0)
_CYAN = (0.0, 1.0, 1.0)
_ORIGIN = (0.0, 0.0, 0.0)


def _point(node: GridNode, offsets: dict[Optional[int], Point]) -> Point:
    offset = offsets[node.grid_id]
    return (float(node.x + offset[0]), float(node.y + offset[1]), float(node.z + offset[2]))


def _route(
    finder: AStarFinder,
    start: GridNode,
    end: GridNode,
    space: Grid | World,
    offsets: dict[Optional[int], Point],
    name: str = "A*",
    color: tuple[float, float, float] = _RED,
) -> Route:
    path, runs = finder.find_path(start, end, space)
    # Materialize both coordinates and scalar cost before resetting node state.
    route = Route(name, [_point(node, offsets) for node in path], float(end.g), int(runs), color)
    space.cleanup()
    return route


def _connected() -> Scenario:
    matrix0 = np.array([[[1, 1, 1], [1, 0, 1], [1, 1, 1]]] * 3)
    matrix1 = matrix0.copy()
    grid0 = Grid(matrix=matrix0, grid_id=0)
    grid1 = Grid(matrix=matrix1, grid_id=1)
    bridge0 = grid0.node(2, 2, 2)
    bridge1 = grid1.node(2, 2, 2)
    bridge0.connect(bridge1)
    bridge1.connect(bridge0)
    world = World({0: grid0, 1: grid1})
    offsets = {0: _ORIGIN, 1: (5.0, 0.0, 0.0)}
    start = grid0.node(2, 0, 0)
    end = grid1.node(2, 0, 0)
    # Use the standard non-diagonal finder and retain the entire world path.
    route = _route(AStarFinder(), start, end, world, offsets)
    return Scenario(
        name="connected",
        title="Connected grids",
        grids=[SceneGrid(matrix0, offsets[0]), SceneGrid(matrix1, offsets[1])],
        routes=[route],
        start=_point(start, offsets),
        end=_point(end, offsets),
        connections=[(_point(bridge0, offsets), _point(bridge1, offsets))],
    )


def build_scenario(name: str) -> Scenario:
    """Build fresh scene data, searching once per algorithm.

    Supported names are the keys of :data:`SCENARIOS`. Unknown names raise
    ValueError. The sample map is loaded relative to this module, not the cwd.
    Route costs are the finder's original end-node costs, not display distances.
    """
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scenario {name!r}. Choose from: {', '.join(SCENARIOS)}")
    if name == "connected":
        return _connected()

    if name == "basic":
        matrix = np.ones((3, 3, 3))
        matrix[1, 1, 1] = 0
        start_xyz, end_xyz = (0, 0, 0), (2, 2, 2)
        diagonal = DiagonalMovement.always
        title = "Basic A* usage"
    elif name == "sample":
        matrix = np.load(Path(__file__).resolve().parent / "sample_map.npy")
        start_xyz, end_xyz = (21, 21, 21), (5, 38, 33)
        diagonal = DiagonalMovement.only_when_no_obstacle
        title = "Sample map"
    else:  # theta
        matrix = np.ones((10, 10, 10), dtype=np.int8)
        matrix[5, 5, 5] = 0
        start_xyz, end_xyz = (0, 0, 0), (9, 9, 9)
        diagonal = DiagonalMovement.always
        title = "Theta* vs A*"

    grid = Grid(matrix=matrix)
    start = grid.node(*start_xyz)
    end = grid.node(*end_xyz)
    offsets = {None: _ORIGIN}
    routes = []
    if name == "theta":
        routes.append(
            _route(
                ThetaStarFinder(diagonal_movement=diagonal),
                start, end, grid, offsets, name="Theta*", color=_CYAN,
            )
        )
    routes.append(_route(AStarFinder(diagonal_movement=diagonal), start, end, grid, offsets))
    return Scenario(
        name=name,
        title=title,
        grids=[SceneGrid(matrix, _ORIGIN)],
        routes=routes,
        start=_point(start, offsets),
        end=_point(end, offsets),
        connections=[],
    )
