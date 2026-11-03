#!/usr/bin/env python3
"""Composite v2 overlays + v2 subtitles over base_preview.mp4 -> final video.
usage: composite.py [out.mp4] [audio.wav]   (audio defaults to base_preview's own track)"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as TL
import build_overlays as BO
EDIT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(EDIT, "final_v3.mp4")
audio = sys.argv[2] if len(sys.argv) > 2 else None
cmd = ["ffmpeg", "-v", "error", "-y", "-i", os.path.join(EDIT, "base_preview.mp4")]
for name, start, dur, items in BO.S:
    cmd += ["-itsoffset", f"{TL.to_video(start):.3f}", "-i", os.path.join(EDIT, "animations_v2", name, "render.mov")]
n = len(BO.S)
if audio: cmd += ["-i", audio]
f, last = [], "0:v"
for i in range(1, n + 1):
    f.append(f"[{last}][{i}:v]overlay=eof_action=pass:format=auto[v{i}]"); last = f"v{i}"
f.append(f"[{last}]ass=filename=master_v2.ass:fontsdir=/usr/share/fonts/truetype/liberation[vout]")
amap = f"{n + 1}:a" if audio else "0:a"
cmd += ["-filter_complex", ";".join(f), "-map", "[vout]", "-map", amap, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", "52.938", "-movflags", "+faststart", out]
subprocess.run(cmd, check=True, cwd=EDIT)
print("wrote", out)
