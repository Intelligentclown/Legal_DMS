"""Generic workflow engine — a configurable state machine. Framework only:
no real workflow definitions ship in Stage 1. The charter's own example
(Draft Created -> Client Review -> Printing -> Registration -> Scanning ->
Completed) is deliberately NOT encoded here — that's business-shaped
configuration a future feature supplies via a `WorkflowDefinition`.
"""
