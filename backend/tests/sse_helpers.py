import json


def parse_sse(text: str) -> list[tuple[str, dict]]:
    """Parse an SSE body into (event, data) pairs. Comments and blank lines are skipped."""
    events = []
    for block in text.split("\n\n"):
        if not block.strip():
            continue
        name, data = "message", None
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line[len("event: ") :]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: ") :])
        events.append((name, data))
    return events
