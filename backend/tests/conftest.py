"""Test setup: isolate job storage to a throwaway temp dir before app import."""
import os
import tempfile

# Must run before `app.core.config` is imported so the storage root is honored.
os.environ.setdefault("ANALYZER_STORAGE", tempfile.mkdtemp(prefix="analyzer-test-"))
os.environ.setdefault("ANALYZER_JOB_TTL", "3600")
