class AgentOutputError(Exception):
    """Agent produced malformed or incomplete CartProposal."""

class AgentToolViolation(Exception):
    """Agent attempted to call a forbidden tool (DB write or payment)."""
