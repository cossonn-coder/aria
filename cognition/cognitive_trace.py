#aria/cognition/cognitive_trace.py
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class TraceStep:

    agent: str
    phase: str  # "before" | "after"
    input_snapshot: Optional[str] = None
    output_snapshot: Optional[str] = None


@dataclass
class CognitiveTrace:

    steps: List[TraceStep] = field(default_factory=list)

    def start(self, agent: str):
        self.steps.append(TraceStep(agent=agent, phase="before"))

    def end(self, output_snapshot: str = ""):
        if not self.steps:
            return

        self.steps[-1].phase = "after"
        self.steps[-1].output_snapshot = output_snapshot

    def as_dict(self):
        return [step.__dict__ for step in self.steps]