"""Generate incident reports from workflow outputs."""


def build_report(result: dict) -> str:
    """Render a simple text report."""
    return "IncidentIQ Plus Report\n\n" + str(result)


def generate(result: dict) -> str:
    """Primary report API used by the incident loop."""
    return build_report(result)
