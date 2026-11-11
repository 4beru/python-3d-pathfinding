"""Compare the documented scenarios in Open3D and Plotly."""
import argparse
import importlib
from pathlib import Path

from scenario_data import SCENARIOS, build_scenario
from scenario_viewers import show_open3d, show_plotly


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List available scenarios and exit")
    parser.add_argument("--scenario", choices=SCENARIOS, help="Scenario to render")
    parser.add_argument("--viewer", choices=("open3d", "plotly", "both"), default="both",
                        help="Viewer to open (default: both)")
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parent / "output",
                        help="Directory for self-contained Plotly HTML files")
    args = parser.parse_args()
    if args.list:
        for name, description in SCENARIOS.items():
            print(f"{name:12} {description}")
        return 0
    if not args.scenario:
        parser.error("select --scenario or use --list")

    required = ("plotly", "open3d") if args.viewer == "both" else (args.viewer,)
    for module in required:
        try:
            importlib.import_module(module)
        except (ImportError, OSError) as error:
            parser.exit(1, f"Cannot load {module}: {error}\n"
                        "Install dependencies from the project root with:\n"
                        "uv pip install --python .venv/bin/python -e '.[vis]' open3d\n")
    try:
        scenario = build_scenario(args.scenario)
        print(f"Scenario: {scenario.name} | {scenario.title}", flush=True)
        print("Colors: start=green, end=magenta, A*=red, Theta*=cyan, obstacles=blue", flush=True)
        for route in scenario.routes:
            print(f"{route.name}: cost={route.cost:.4f}, points={len(route.points)}, runs={route.runs}",
                  flush=True)
            if not route.points:
                print(f"Warning: no path found for {route.name}", flush=True)
        if scenario.connections:
            print("Connected grids use display-only offsets. Orange marks their connection.\n"
                  "Reported cost uses the original grid coordinates, not display distances.", flush=True)
        if args.viewer in ("plotly", "both"):
            show_plotly(scenario, args.output_dir)
        if args.viewer in ("open3d", "both"):
            show_open3d(scenario)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 130
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(1, f"Unable to display scenario: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
