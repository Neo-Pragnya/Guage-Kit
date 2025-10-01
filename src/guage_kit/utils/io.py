from pathlib import Path
import json

def write_artifact(file_path: str, data: dict) -> None:
    """Write data to a JSON file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def read_artifact(file_path: str) -> dict:
    """Read data from a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def manage_run_registry(run_id: str, run_data: dict, registry_path: str) -> None:
    """Manage run registry by saving run data."""
    registry_file = Path(registry_path) / f"{run_id}.json"
    write_artifact(str(registry_file), run_data)

def load_run(run_id: str, registry_path: str) -> dict:
    """Load a specific run's data from the registry."""
    registry_file = Path(registry_path) / f"{run_id}.json"
    return read_artifact(str(registry_file)) if registry_file.exists() else {}