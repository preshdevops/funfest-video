"""Shared timeline (seconds) for the Fun Fest 1.0 vertical teaser. Visuals and music both read this."""
FPS = 30
DUR = 13.6

# beat 1: "COMING SOON" posters stack up, accelerating, then dim
POSTER_T = [0.10, 0.55, 0.95, 1.30, 1.60, 1.85, 2.08, 2.28, 2.46, 2.62, 2.77, 2.91, 3.04, 3.15, 3.25, 3.34, 3.42]
POSTER_DIM = (3.35, 3.60)

# beat 2: "ARE YOU READY?" stutter, hit, ghost echo, zoom-through
READY_T0 = 3.60
READY_HITS = (3.80, 4.15, 4.45)
READY_END = 6.30

# beat 3: diagonal slices of the speakers, one per beat (~96.8 bpm)
SLICE_T0 = 6.40
SLICE_DUR = 0.62
N_SLICE = 6

# beat 4: the name reveal
REVEAL = round(SLICE_T0 + SLICE_DUR * N_SLICE, 2)   # 10.12
