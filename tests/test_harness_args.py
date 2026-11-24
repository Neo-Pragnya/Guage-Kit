"""How Ananke evaluator arguments are declared and filled."""

from __future__ import annotations

from guage_kit.core.sample import Sample
from guage_kit.harness.catalogue import _resolve_args, discover
from guage_kit.metrics.registry import list_metrics


def test_required_and_optional_arguments_are_told_apart() -> None:
    by_name = {m["name"]: m for m in list_metrics() if m["source"] == "ananke-plexus"}
    conformance = by_name["ananke.architecture.model_conformance"]
    assert conformance["required_params"] == ["required_fields"]
    scope = by_name["ananke.safety.secret_access"]
    assert (
        "restricted_paths" in scope["params"] and "restricted_paths" not in scope["required_params"]
    )


def test_a_flat_list_gives_a_single_step_argument_its_goal() -> None:
    ev = discover()["ananke.trajectory.required_step"]
    assert ev.annotations.get("required", "").strip() == "str"
    sample = Sample(
        id="1", input="book a room", metadata={"ananke": {"required": ["search", "book"]}}
    )
    args, missing = _resolve_args(ev, sample, {})
    assert args["required"] == "book" and not missing
