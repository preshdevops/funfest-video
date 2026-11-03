#!/usr/bin/env python3
"""Cut six expressive speaker moments into 1080x1920 frame sequences for the teaser slices.
Needs edit/clips_preview/*.mp4 (git lfs pull). Output: <assets>/slices/<i>/%03d.jpg"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); EDIT = os.path.abspath(os.path.join(HERE, ".."))
A = os.environ.get("TEASER_ASSETS", os.path.join(EDIT, "teaser_assets"))
# (clip, position in clip 0..1, horizontal face position 0..1)
PICKS = [("seg_00_1", 0.70, 0.49), ("seg_09_10", 0.25, 0.50), ("seg_08_9", 0.70, 0.44),
         ("seg_05_5", 0.25, 0.46), ("seg_06_6", 0.70, 0.49), ("seg_14_15", 0.70, 0.45)]
for i, (clip, pos, face) in enumerate(PICKS):
    src = os.path.join(EDIT, "clips_preview", clip + ".mp4")
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src]))
    t0 = max(0.0, dur * pos - 0.30)
    x = int(min(max(face * 1920 - 304, 0), 1312)) // 2 * 2
    out = os.path.join(A, "slices", str(i)); os.makedirs(out, exist_ok=True)
    for f in os.listdir(out): os.remove(os.path.join(out, f))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-i", src, "-t", "0.74", "-an",
                    "-vf", f"fps=30,crop=608:1080:{x}:0,scale=1080:1920:flags=lanczos,unsharp=5:5:0.6",
                    "-q:v", "3", os.path.join(out, "%03d.jpg")], check=True)
    print(i, clip, "t0=%.2f x=%d frames=%d" % (t0, x, len(os.listdir(out))))
