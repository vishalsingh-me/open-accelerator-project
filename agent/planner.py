"""Action planning module for incident remediation."""


class Planner:
    """Build remediation plans from analysis artifacts."""

    def plan(self, analysis: dict) -> dict:
        """Create a minimal action plan."""
        _ = analysis
        return {"actions": [], "notes": "Planning not implemented."}
