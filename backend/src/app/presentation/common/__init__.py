"""Reusable presentation-layer building blocks: the response envelope and
(later in Stage 1) the generic CRUD router factory. `/health` and `/version`
intentionally stay unwrapped — this envelope is for future resource-
returning endpoints, not a retroactive change to the existing probes.
"""
