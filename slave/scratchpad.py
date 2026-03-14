class Scratchpad:
    """Accumulates the thought/action/observation trace for a slave agent."""

    def __init__(self):
        raise NotImplementedError

    def add(self, role: str, content: str) -> None:
        raise NotImplementedError

    def to_messages(self) -> list[dict]:
        raise NotImplementedError

    def summary(self) -> str:
        raise NotImplementedError
