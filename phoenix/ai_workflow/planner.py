"""Dependency-aware workflow planning."""

from __future__ import annotations

from collections import defaultdict, deque

from .models import WorkflowDefinition, WorkflowStep


class WorkflowPlanner:
    """Validates and topologically orders workflow steps."""

    def plan(self, workflow: WorkflowDefinition) -> list[WorkflowStep]:
        by_name = {}
        for step in workflow.steps:
            if step.name in by_name:
                raise ValueError(f"duplicate workflow step name: {step.name}")
            by_name[step.name] = step

        indegree = {name: 0 for name in by_name}
        outgoing: dict[str, list[str]] = defaultdict(list)

        for step in workflow.steps:
            for dependency in step.depends_on:
                if dependency not in by_name:
                    raise KeyError(
                        f"step '{step.name}' depends on unknown step '{dependency}'"
                    )
                indegree[step.name] += 1
                outgoing[dependency].append(step.name)

        queue = deque(sorted(name for name, degree in indegree.items() if degree == 0))
        ordered = []

        while queue:
            name = queue.popleft()
            ordered.append(by_name[name])
            for child in sorted(outgoing[name]):
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)

        if len(ordered) != len(workflow.steps):
            raise ValueError("workflow dependency cycle detected")

        return ordered
