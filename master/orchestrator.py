class Orchestrator:
    """Top-level loop: plan -> dispatch -> review -> assemble."""

    def __init__(self):
        raise NotImplementedError

    def run(self, user_goal: str) -> str:
        raise NotImplementedError
