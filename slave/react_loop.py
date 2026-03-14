class ReActLoop:
    """Implements the Thought -> Action -> Observation loop for a slave agent."""

    def __init__(self, system_prompt: str, max_iterations: int = 15):
        raise NotImplementedError

    def step(self, observation: str) -> tuple[str, str]:
        raise NotImplementedError

    def is_done(self) -> bool:
        raise NotImplementedError
