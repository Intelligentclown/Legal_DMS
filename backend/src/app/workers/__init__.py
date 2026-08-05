"""Background job processing: the `JobRegistry` maps job names to `Job`
implementations that a `JobQueue` executes. Real business jobs (OCR, PDF
conversion, backups, ...) arrive with the feature that needs them — Stage 1
only ships the framework plus a trivial no-op job proving it end to end.
"""
