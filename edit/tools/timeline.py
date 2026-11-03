"""Map times from the edit-list (audio) timeline to the real video timeline.
The segment clips are a few ms longer in video than in audio, so by the end of the
cut the picture runs ~0.32s later than the EDL timeline the captions/overlays were
first authored on."""
import bisect
EDL_DUR = [2.68, 1.76, 4.96, 4.02, 2.15, 5.90, 5.10, 4.22, 3.24, 1.68, 2.54, 2.38, 3.06, 2.92, 3.48, 2.50]
VID_DUR = [2.717722, 1.760778, 4.976111, 4.057444, 2.181833, 5.933056, 5.129222, 4.248833,
           3.253611, 1.684222, 2.564611, 2.4115, 3.062222, 2.947389, 3.483278, 2.526333]
ES, VS = [0.0], [0.0]
for a, b in zip(EDL_DUR, VID_DUR):
    ES.append(ES[-1] + a); VS.append(VS[-1] + b)
SHIFT = [VS[i] - ES[i] for i in range(16)]

def to_video(t):
    i = min(max(bisect.bisect_right(ES, t + 1e-6) - 1, 0), 15)
    return t + SHIFT[i]
