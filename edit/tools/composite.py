#!/usr/bin/env python3
"""Composite v2 overlays + v2 subtitles over base_preview.mp4 -> final_v2.mp4 (audio copied from base)."""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); EDIT = os.path.abspath(os.path.join(HERE, ".."))
edl = json.load(open(os.path.join(EDIT, "edl.json")))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(EDIT, "final_v2.mp4")
ss = ["-ss", sys.argv[2], "-t", sys.argv[3]] if len(sys.argv) > 3 else []
cmd = ["ffmpeg", "-v", "error", "-y", "-i", os.path.join(EDIT, "base_preview.mp4")]
for o in edl["overlays"]:
    cmd += ["-itsoffset", f"{o['start_in_output']:.3f}", "-i", os.path.join(EDIT, o["file"].replace("animations/", "animations_v2/"))]
f, last = [], "0:v"
for i in range(1, len(edl["overlays"]) + 1):
    f.append(f"[{last}][{i}:v]overlay=eof_action=pass:format=auto[v{i}]"); last = f"v{i}"
f.append(f"[{last}]ass=filename=master_v2.ass:fontsdir=/usr/share/fonts/truetype/liberation[vout]")
cmd += ["-filter_complex", ";".join(f), "-map", "[vout]", "-map", "0:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart"] + ss + [out]
print(" ".join(cmd[:6]), "...")
subprocess.run(cmd, check=True, cwd=EDIT)
