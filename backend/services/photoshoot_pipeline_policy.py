"""Which of the four stages run for a given input_kind / overlay."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StagePlan:
    name: str
    status: str  # pending | skipped


def plan(input_kind: str, has_overlay: bool) -> list[StagePlan]:
    tryoff = "skipped" if input_kind == "flat_garment" else "pending"
    composition = "pending" if has_overlay else "skipped"
    return [
        StagePlan("tryoff", tryoff),
        StagePlan("vton", "pending"),
        StagePlan("poses", "pending"),
        StagePlan("composition", composition),
    ]
