#!/usr/bin/env python3
"""Rebuild subtitles: regroup the raw word timings into natural phrases and fix text
(ordinals 2ND/4TH/5TH, OSOGBO, IFETEDO, FUN FEST 1.0! kept together). Writes master_v2.srt + master_v2.ass."""
import re, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as TL
HERE = os.path.dirname(os.path.abspath(__file__)); EDIT = os.path.join(HERE, "..")

def tc(s):
    h, m, r = s.split(":"); sec, ms = r.split(",")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000

cues = []
for blk in open(os.path.join(EDIT, "master.srt"), encoding="utf-8").read().strip().split("\n\n"):
    lines = blk.split("\n")
    a, b = lines[1].split(" --> ")
    cues.append((TL.to_video(tc(a)), TL.to_video(tc(b)), lines[2].split()))

words = []  # (word, start, end) - words spread across each cue by character length
for s, e, toks in cues:
    tot = sum(len(t) + 1 for t in toks); t0 = s
    for t in toks:
        d = (e - s) * (len(t) + 1) / tot
        words.append((t, t0, t0 + d)); t0 += d

# (display text, number of original words consumed)
G = [("SCHOOL IS BACK",3),("AND LECTURES ARE BACK",4),("ASSIGNMENTS ARE BACK TOO.",4),("AND IF YOU ARE",4),
 ("JUST RESUMING,",2),("YOU ARE PROBABLY",3),("STILL FIGURING OUT",3),("HOW EVERYTHING WORKS.",3),
 ("WELL, FRESHER OR",3),("RETURNING STUDENT,",2),("WE'VE GOT SOMETHING",3),("FOR YOU:",2),("FUN FEST 1.0!",3),
 ("AND OF COURSE,",3),("WE ARE BRINGING IN",4),("FUN, GAMES,",2),("NEW FRIENDS,",2),("AND A CHANCE",3),
 ("TO CONNECT",2),("WITH OTHER STUDENTS.",3),("BUT IT'S NOT JUST FUN.",5),("YOU WILL ALSO",3),
 ("PICK UP SKILLS",3),("THAT CAN ACTUALLY",3),("HELP YOU",2),("LEARN HOW TO",3),("BUILD A CV,",3),
 ("SET UP YOUR LINKEDIN,",4),("AND FIND OPPORTUNITIES",3),("WORTH GOING FOR.",3),("AND MOST IMPORTANTLY,",3),
 ("YOU WOULD EXPERIENCE",3),("GOD'S LOVE.",2),("SO, WHERE ARE WE MEETING?",5),
 ("OKUKU, WEDNESDAY",2),("DECEMBER 2ND",2),("OSOGBO, FRIDAY",2),("DECEMBER 4TH",2),
 ("IFETEDO, SATURDAY",2),("DECEMBER 5TH",2),("DIFFERENT CAMPUSES,",2),("SAME GOOD TIME.",3),
 ("YES, YOU!",2),("INVITE YOUR FRIENDS",3),("AND SAVE THE DATE.",4),("SEE YOU AT",3),("FUN FEST 1.0!",3)]
assert sum(n for _, n in G) == len(words), (sum(n for _, n in G), len(words))

groups, i = [], 0
for txt, n in G:
    groups.append([txt, words[i][1], words[i + n - 1][2]]); i += n
# hold each group until the next starts (max 0.25s past its own end), min 0.45s on screen
for k, g in enumerate(groups):
    nxt = groups[k + 1][1] if k + 1 < len(groups) else g[2] + 0.6
    g[2] = max(min(nxt - 0.02, g[2] + 0.25), g[1] + 0.45)
    if k + 1 < len(groups): g[2] = min(g[2], groups[k + 1][1] - 0.02)

def srt_t(t): ms = int(round(t * 1000)); return f"{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}"
def ass_t(t): cs = int(round(t * 100)); return f"{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}"

open(os.path.join(EDIT, "master_v2.srt"), "w", encoding="utf-8").write(
    "\n".join(f"{k+1}\n{srt_t(a)} --> {srt_t(b)}\n{t}\n" for k, (t, a, b) in enumerate(groups)))

hdr = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Liberation Sans,74,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,1,2,80,80,170,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
ev = "".join(f"Dialogue: 0,{ass_t(a)},{ass_t(b)},Default,,0,0,0,,{{\\fad(40,50)\\fscx88\\fscy88\\t(0,110,\\fscx100\\fscy100)}}{t}\n" for t, a, b in groups)
open(os.path.join(EDIT, "master_v2.ass"), "w", encoding="utf-8").write(hdr + ev)
print(len(groups), "subtitle groups"); [print(f"{a:6.2f}-{b:6.2f}  {t}") for t, a, b in groups]
