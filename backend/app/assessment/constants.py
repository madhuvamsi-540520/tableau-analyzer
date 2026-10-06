"""Thresholds for the deterministic assessment (documented so they are tunable)."""

EXCESSIVE_JOINS = 5          # joins per data source above which complexity is flagged
MANY_CALCS = 25             # calculated fields above which maintainability is a concern
LARGE_TABLE_ROWS = 1_000_000
LARGE_DIM_ROWS = 200_000
COMPLEX_SQL_SCORE = 3        # CTEs + subqueries + window functions
