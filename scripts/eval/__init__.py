"""Evaluation harness: measures the tabgen pipeline against annotated datasets.

Lives outside ``tabgen/core`` on purpose: it depends on datasets that are
downloaded (with explicit user confirmation) into a directory outside the
repository, and it only *measures* the pipeline (no training, no tuning).
"""
