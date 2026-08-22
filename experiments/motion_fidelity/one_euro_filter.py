"""One-Euro Filter (Casiez, Roussel, Vogel 2012) — adaptive low-pass
filter for noisy signals from human interaction, specifically designed
for exactly this problem: reduce jitter on slow/near-still motion
without adding noticeable lag on fast motion. The alternative (a fixed-
alpha EMA, which is what smooth_xyz/prod_smooth already do throughout
this codebase) is a blunt instrument — one alpha value is either too
smooth (laggy, "stitched-together" feeling on fast real motion like the
circle sign) or too jittery (on slow/held motion), never both right.

Standard reference implementation, adapted only to operate on plain
(x, y, z) tuples per landmark rather than scalars, and to reset cleanly
across detection gaps (matching this codebase's existing gap-reset
convention in smooth_series/smooth_xyz) rather than filtering through
a hole with fabricated data.
"""
import math


class _LowPassFilter:
    def __init__(self):
        self.y = None
        self.s = None

    def filter(self, x, alpha):
        if self.y is None:
            self.y = self.s = x
        else:
            self.s = alpha * x + (1 - alpha) * self.s
            self.y = x
        return self.s

    def last_value(self):
        return self.y


def _alpha(cutoff, dt):
    tau = 1.0 / (2 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


class OneEuroFilter1D:
    """Filters a single scalar time series. min_cutoff controls the
    baseline amount of smoothing (lower = smoother at rest); beta
    controls how much high-speed motion is allowed to cut through that
    smoothing (higher = less lag when moving fast)."""

    def __init__(self, min_cutoff=1.0, beta=0.3, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_filter = _LowPassFilter()
        self.dx_filter = _LowPassFilter()
        self.last_x = None

    def reset(self):
        self.x_filter = _LowPassFilter()
        self.dx_filter = _LowPassFilter()
        self.last_x = None

    def filter(self, x, dt):
        if self.last_x is None:
            dx = 0.0
        else:
            dx = (x - self.last_x) / dt if dt > 0 else 0.0
        self.last_x = x

        edx = self.dx_filter.filter(dx, _alpha(self.d_cutoff, dt))
        cutoff = self.min_cutoff + self.beta * abs(edx)
        return self.x_filter.filter(x, _alpha(cutoff, dt))


class OneEuroFilterND:
    """Filters a tuple of independent scalars (e.g. one landmark's
    (x, y, z)) — one OneEuroFilter1D per dimension."""

    def __init__(self, n_dims, min_cutoff=1.0, beta=0.3, d_cutoff=1.0):
        self.filters = [OneEuroFilter1D(min_cutoff, beta, d_cutoff) for _ in range(n_dims)]

    def reset(self):
        for f in self.filters:
            f.reset()

    def filter(self, values, dt):
        return tuple(f.filter(v, dt) for f, v in zip(self.filters, values))


def one_euro_smooth_series(series, fps, min_cutoff=1.0, beta=0.3):
    """Drop-in replacement for the fixed-alpha smooth_xyz()/smooth_series()
    pattern already used throughout this codebase, but adaptive per-
    landmark. series: list of Optional[list of (x,y,z) tuples] (one hand's
    21 landmarks per frame) or Optional[dict] (pose). Resets filters at
    every detection gap, same convention as the existing smoothers — a
    gap is a real absence, not something to filter through."""
    dt = 1.0 / fps if fps else 1.0 / 25
    out = [None] * len(series)
    filters = None  # lazily created per-landmark on first real frame after a gap
    for i, v in enumerate(series):
        if v is None:
            filters = None
            continue
        if isinstance(v, dict):
            if filters is None:
                filters = {k: OneEuroFilterND(2, min_cutoff, beta) for k in v}
            out[i] = {k: filters[k].filter(v[k][:2], dt) for k in v}
        else:  # list of (x,y,z) tuples
            if filters is None:
                filters = [OneEuroFilterND(len(v[0]), min_cutoff, beta) for _ in v]
            out[i] = [filters[j].filter(pt, dt) for j, pt in enumerate(v)]
    return out
