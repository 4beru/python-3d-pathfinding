"""Render shared scenario data without recalculating paths."""
from pathlib import Path
import webbrowser

import numpy as np


def _rgb(color):
    return "rgb({},{},{})".format(*(round(channel * 255) for channel in color))


def _bounds(scene_grid):
    low = np.asarray(scene_grid.offset, dtype=float) - 0.5
    high = low + np.asarray(scene_grid.matrix.shape)
    corners = np.array([
        [x, y, z] for x in (low[0], high[0])
        for y in (low[1], high[1]) for z in (low[2], high[2])
    ])
    edges = [(i, j) for i in range(8) for j in range(i + 1, 8)
             if bin(i ^ j).count("1") == 1]
    return corners, edges


def show_plotly(scenario, output_dir):
    """Save a self-contained HTML file, then request browser opening."""
    import plotly.graph_objects as go

    traces = []
    for index, scene_grid in enumerate(scenario.grids):
        obstacles = np.argwhere(scene_grid.matrix <= 0) + np.asarray(scene_grid.offset)
        if len(obstacles):
            traces.append(go.Scatter3d(
                x=obstacles[:, 0], y=obstacles[:, 1], z=obstacles[:, 2],
                mode="markers", marker=dict(size=5, color="royalblue", opacity=0.4),
                name=f"Obstacles {index}",
            ))
        corners, edges = _bounds(scene_grid)
        coordinates = [[value for i, j in edges
                        for value in (corners[i, axis], corners[j, axis], None)]
                       for axis in range(3)]
        traces.append(go.Scatter3d(
            x=coordinates[0], y=coordinates[1], z=coordinates[2],
            mode="lines", line=dict(color="gray", width=2), name=f"Grid {index}",
            hoverinfo="skip",
        ))
    for route in scenario.routes:
        if route.points:
            points = np.asarray(route.points)
            traces.append(go.Scatter3d(
                x=points[:, 0], y=points[:, 1], z=points[:, 2],
                mode="lines+markers", name=route.name,
                marker=dict(size=3, color=_rgb(route.color)),
                line=dict(width=6, color=_rgb(route.color)),
            ))
    for first, last in scenario.connections:
        traces.append(go.Scatter3d(
            x=[first[0], last[0]], y=[first[1], last[1]], z=[first[2], last[2]],
            mode="lines", line=dict(color="orange", width=5, dash="dash"),
            name="Grid connection (display offset)",
        ))
    for name, point, color in (("Start", scenario.start, "limegreen"),
                               ("End", scenario.end, "magenta")):
        traces.append(go.Scatter3d(
            x=[point[0]], y=[point[1]], z=[point[2]], mode="markers", name=name,
            marker=dict(size=8, color=color),
        ))
    figure = go.Figure(traces)
    figure.update_layout(
        title=scenario.title,
        scene=dict(aspectmode="data", xaxis_title="X", yaxis_title="Y", zaxis_title="Z"),
        margin=dict(l=0, r=0, b=0, t=45),
    )
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{scenario.name}.html"
    figure.write_html(str(output), include_plotlyjs=True, auto_open=False)
    print(f"Plotly HTML: {output}", flush=True)
    try:
        opened = webbrowser.open(output.as_uri(), new=2)
    except (webbrowser.Error, OSError) as error:
        print(f"Browser could not be opened: {error}", flush=True)
        opened = False
    if not opened:
        print("Open the printed HTML file manually to view Plotly.", flush=True)


def show_open3d(scenario):
    """Open a desktop viewer with obstacles, routes and grid boundaries."""
    import open3d as o3d

    geometries = []

    def add_lines(points, edges, color):
        if not edges:
            return
        lines = o3d.geometry.LineSet()
        lines.points = o3d.utility.Vector3dVector(np.asarray(points, dtype=float))
        lines.lines = o3d.utility.Vector2iVector(np.asarray(edges, dtype=np.int32))
        lines.paint_uniform_color(color)
        geometries.append(lines)

    for scene_grid in scenario.grids:
        obstacles = np.argwhere(scene_grid.matrix <= 0) + np.asarray(scene_grid.offset)
        if len(obstacles):
            # Explicit bounds align voxel centers with integer route coordinates.
            cloud = o3d.geometry.PointCloud()
            cloud.points = o3d.utility.Vector3dVector(obstacles.astype(float))
            cloud.paint_uniform_color([0.2, 0.4, 0.8])
            low = np.asarray(scene_grid.offset, dtype=float) - 0.5
            high = low + np.asarray(scene_grid.matrix.shape)
            geometries.append(o3d.geometry.VoxelGrid.create_from_point_cloud_within_bounds(
                cloud, 1.0, low, high,
            ))
        corners, edges = _bounds(scene_grid)
        add_lines(corners, edges, [0.5, 0.5, 0.5])
    for route in scenario.routes:
        add_lines(route.points, [(i, i + 1) for i in range(len(route.points) - 1)], route.color)
    for first, last in scenario.connections:
        add_lines([first, last], [(0, 1)], [1.0, 0.6, 0.0])
    for point, color in ((scenario.start, [0.2, 1.0, 0.2]), (scenario.end, [1.0, 0.0, 1.0])):
        marker = o3d.geometry.TriangleMesh.create_sphere(radius=0.22)
        marker.compute_vertex_normals()
        marker.paint_uniform_color(color)
        marker.translate(point)
        geometries.append(marker)
    print("Open3D: focus the 3D window and press Q or Esc to close it.", flush=True)
    o3d.visualization.draw_geometries(
        geometries, window_name=scenario.title, width=1024, height=768,
    )
