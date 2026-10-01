#!/usr/bin/env python3
"""Render the runanchor submission demo video — deterministic, no screen capture.

PIL draws 1920x1080 frames per scene, macOS `say` generates the narration,
ffmpeg assembles an H.264+AAC mp4 (YouTube-compatible).

Deps (NOT package deps — submission tooling only):
    pip install Pillow   ·   ffmpeg   ·   macOS `say`

Inputs are real artifacts: terminal text is captured verbatim from
`runanchor demo/list/show` on a fixture ledger; measured numbers are the v3
bench values also printed in README/form-answers. Narration lines must stay
inside submit/narration-claims.md (claims SSOT) — each is tagged below.

Usage:
    python3 scripts/render_demo_video_runanchor.py \
        --workdir /tmp/ra-video --out submit/runanchor-demo.mp4
"""

import argparse
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 1920, 1080

# palette — matches docs/architecture.svg (GitHub-dark-adjacent)
BG = "#0D1117"
PANEL = "#161B22"
PANEL2 = "#1C2230"
BORDER = "#30363D"
TEXT = "#E6EDF3"
DIM = "#8B949E"
GREEN = "#3FB950"
RED = "#F85149"
CYAN = "#79C0FF"
YELLOW = "#D29922"
ORANGE = "#E8890C"

MONO = "/System/Library/Fonts/SFNSMono.ttf"
DISP = "/System/Library/Fonts/SFNS.ttf"

_fonts: dict = {}


def font(size: int, mono: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, mono)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(MONO if mono else DISP, size)
    return _fonts[key]


def new_frame() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def text_size(draw: ImageDraw.ImageDraw, s: str, f: ImageFont.FreeTypeFont) -> tuple[int, int]:
    l, t, r, b = draw.textbbox((0, 0), s, font=f)
    return r - l, b - t


def center_text(draw, y: int, s: str, f, color=TEXT, stroke: int = 0) -> int:
    tw, th = text_size(draw, s, f)
    draw.text(((W - tw) / 2, y), s, font=f, fill=color,
              stroke_width=stroke, stroke_fill=color)
    return y + th


def footer(draw, scene_no: int, total: int = 7) -> None:
    draw.text((60, H - 56), "runanchor", font=font(22, mono=True), fill=DIM)
    dots = "\u2009".join("\u25cf" if i == scene_no else "\u25cb" for i in range(1, total + 1))
    tw, _ = text_size(draw, dots, font(16))
    draw.text((W - 60 - tw, H - 52), dots, font=font(16), fill=DIM)


# ---------- terminal rendering ----------

LINE_H = 46
TERM_X, TERM_Y, TERM_W = 180, 150, W - 360
PROMPT = "$ "


def term_window(lines: list[list[tuple[str, str]]], title: str) -> Image.Image:
    """lines: list of rows; each row = list of (text, style) segments."""
    img, d = new_frame()
    rows = max(len(lines), 1)
    wh = 90 + rows * LINE_H + 36
    ty = (H - wh) // 2  # vertically center the window
    d.rounded_rectangle([TERM_X, ty, TERM_X + TERM_W, ty + wh],
                        radius=18, fill=PANEL, outline=BORDER, width=2)
    for i, c in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
        d.ellipse([TERM_X + 30 + i * 30, ty + 28, TERM_X + 50 + i * 30, ty + 48], fill=c)
    d.text((TERM_X + 130, ty + 24), title, font=font(24, mono=True), fill=DIM)

    style_color = {"": TEXT, "dim": DIM, "green": GREEN, "red": RED,
                   "cyan": CYAN, "yellow": YELLOW, "orange": ORANGE}
    for r, row in enumerate(lines):
        x = TERM_X + 44
        y = ty + 90 + r * LINE_H
        hl = next((s for t, s in row if s.startswith("hl")), None)
        for t, s in row:
            color = style_color.get(s.replace("hl", ""), TEXT)
            if hl:
                d.rounded_rectangle([x - 12, y - 4, x + text_size(d, t, font(27, True))[0] + 12,
                                     y + LINE_H - 10], radius=8, outline=CYAN, width=2)
            d.text((x, y), t, font=font(27, mono=True), fill=color)
            x += text_size(d, t, font(27, mono=True))[0]
    return img


def reveal_frames(lines: list, title: str, pre: float = 0.9, tail: float = 4.0) -> list[tuple[Image.Image, float]]:
    """Progressive line reveal; returns (image, relative weight) list."""
    frames = [(term_window(lines[:1], title), pre)]
    for i in range(2, len(lines) + 1):
        frames.append((term_window(lines[:i], title), 1.0))
    frames[-1] = (frames[-1][0], tail)
    return frames


# ---------- scenes ----------

# narration: every line maps to a verified row in submit/narration-claims.md
NARR = {
    1: "AI agents say: done, tests pass. Who checks that? CI checks artifacts. "
       "Nobody checks the agent's report. runanchor does.",                    # claim 1
    2: "Every run gets a receipt, anchored to the provider's own execution "
       "record — not the agent's self report. Three runs: a real failure, a "
       "false success claim — rejected — and a verified fix, adopted.",        # claim 2
    3: "Not a self report. A verifiable record. Provider issued operation and "
       "image IDs, stream fingerprints, and the decision: adopted only after "
       "replay verifies.",                                                    # claim 3+4
    4: "Two independent checks. Replay forks the recorded start image and "
       "reruns the command — a reported but not run claim cannot survive "
       "re-execution. The hidden oracle runs tests the agent never saw, "
       "mounted outside its workspace under an isolated interpreter — so "
       "green but wrong cannot survive either.",                              # claim 4+4b
    5: "We measured the gate itself, on live Nebius sandboxes. Reading "
       "evidence alone, the judge caught three of five defective runs. With "
       "replay and the hidden oracle — all five, while passing twenty nine of "
       "thirty good runs. The corpus, the judge prompt, and the ledger are in "
       "the repo: check our numbers, not our claims.",                        # claim 5+6
    6: "Under the hood: ConTree sandbox operations anchor every receipt. "
       "Nemotron plans the agent loop; Nemotron judges the evidence. "
       "Everything lands on an append only, hash chained ledger — even the "
       "failures.",                                                           # claim 7
    7: "runanchor. MIT licensed, offline demo in the repo. Check our numbers, "
       "not our claims.",                                                     # claim 6
}

MIN_DUR = {1: 7.0, 2: 20.0, 3: 22.0, 4: 24.0, 5: 24.0, 6: 16.0, 7: 6.5}


def scene1() -> list[tuple[Image.Image, float]]:
    img, d = new_frame()
    y = 330
    y = center_text(d, y, "runanchor", font(120, mono=True), TEXT, stroke=1) + 30
    y = center_text(d, y, "receipts your coding agent can't fake", font(44), CYAN) + 90
    y = center_text(d, y, "\u201cAI agents say: done, tests pass.\u201d", font(36), DIM) + 8
    center_text(d, y, "Who checks the report?", font(36), YELLOW)
    footer(d, 1)
    return [(img, 1.0)]


def scene2() -> list[tuple[Image.Image, float]]:
    L = [[(PROMPT, "green"), ("runanchor demo", "")]]
    L += [
        [("[DEMO] image selected: ", "dim"), ("demo:base-image", "cyan")],
        [("[DEMO] run 1: ", "dim"), ("status=FAILED", "red"), (" exit=1  receipt=22395c62", "dim")],
        [("[DEMO] run 2: ", "dim"), ("status=FAILED", "red"), (" exit=1  receipt=29626b97", "dim")],
        [("[DEMO] run 3: ", "dim"), ("status=SUCCESS", "green"), (" exit=0 receipt=3843d895", "dim")],
        [("[DEMO] verify 3843d895: ", "dim"), ("match", "green")],
        [("[DEMO] hidden oracle on result image: ", "dim"), ("pass", "green")],
        [("[DEMO] rejected 29626b97 ", "red"), ("(false success claim)", "orange")],
        [("[DEMO] adopted 3843d895", "green")],
        [("[DEMO] ledger: 3 receipts | ", "dim"), ("adopted=1", "green"), (" ", "dim"), ("rejected=1", "red")],
    ]
    return reveal_frames(L, "runanchor — demo (offline fixtures)")


def scene3() -> list[tuple[Image.Image, float]]:
    # list output
    A = [[(PROMPT, "green"), ("runanchor list", "")],
         [("22395c62  demo-fix-sort#1  ", "dim"), ("FAILED", "red"), ("   exit=1  state=pending", "dim")],
         [("29626b97  demo-fix-sort#2  ", "dim"), ("FAILED", "red"), ("   exit=1  state=rejected", "orange")],
         [("3843d895  demo-fix-sort#3  ", "dim"), ("SUCCESS", "green"), ("  exit=0  state=adopted", "green")]]
    # show output — real fields, order preserved, long hashes elided with …
    B = [[(PROMPT, "green"), ("runanchor show 3843d895", "")],
         [("== DEMO receipt (fixture-anchored, not a live run) ==", "yellow")],
         [("receipt_id: ", "dim"), ("3843d895164b451d9366704281338b78", "cyanhl")],
         [("task: ", "dim"), ("demo-fix-sort    ", ""), ("state: ", "dim"), ("adopted", "green")],
         [("status: SUCCESS   exit_code: 0   command: pytest -q", "")],
         [("operation_uuid: ", "dim"), ("demo-op-3", "cyanhl")],
         [("image_uuid: ", "dim"), ("img-demo-b", "cyanhl"), ("   result_image_uuid: ", "dim"), ("img-demo-c", "cyanhl")],
         [("stdout_sha256: ", "dim"), ("76085f31727816f3fbe1…", "")],
         [("decision: ", "dim"), ("{'by': 'human', 'reason': 'replay verified', …}", "hl")],
         [("…", "dim")]]
    fa = reveal_frames(A, "runanchor — receipts on the ledger")
    fb = reveal_frames(B, "runanchor — one receipt, provider-anchored")
    return fa + fb


def _box(d, xy, title, sub=None, accent=CYAN, fill=PANEL):
    x0, y0, x1, y1 = xy
    d.rounded_rectangle(xy, radius=14, fill=fill, outline=BORDER, width=2)
    d.text((x0 + 26, y0 + 18), title, font=font(30), fill=accent)
    if sub:
        d.text((x0 + 26, y0 + 62), sub, font=font(24, mono=True), fill=DIM)


def _arrow(d, x0, y, x1, color=DIM):
    d.line([x0, y, x1 - 14, y], fill=color, width=4)
    d.polygon([(x1 - 14, y - 10), (x1, y), (x1 - 14, y + 10)], fill=color)


def scene4() -> list[tuple[Image.Image, float]]:
    """Two verification axes; phase 1 shows replay only, phase 2 adds oracle."""
    # column layout: axis 200 | arrow 60 | box 420 | arrow 60 | box 500 | arrow 60 | verdict 260 = 1560
    c = [TERM_X, TERM_X + 200, TERM_X + 260, TERM_X + 680, TERM_X + 740,
         TERM_X + 1240, TERM_X + 1300, TERM_X + TERM_W]

    def draw(phase2: bool) -> Image.Image:
        img, d = new_frame()
        center_text(d, 110, "verify on two independent axes", font(48), TEXT)
        y1, y2 = 320, 620
        bh = 130
        # axis 1: replay — always visible
        _box(d, (c[0], y1, c[1], y1 + bh), "REPLAY", None, CYAN)
        _box(d, (c[2], y1, c[3], y1 + bh), "start image", "recorded at run time", DIM)
        _box(d, (c[4], y1, c[5], y1 + bh), "rerun command", "exit + stream fingerprints", DIM)
        _box(d, (c[6], y1, c[7], y1 + bh), "match", "no-run dies", GREEN)
        for x0, x1 in ((c[1], c[2]), (c[3], c[4]), (c[5], c[6])):
            _arrow(d, x0, y1 + bh // 2, x1)
        if phase2:
            _box(d, (c[0], y2, c[1], y2 + bh), "ORACLE", "hidden", YELLOW)
            _box(d, (c[2], y2, c[3], y2 + bh), "result image", "the produced state", DIM)
            _box(d, (c[4], y2, c[5], y2 + bh), "unseen tests", "outside /work · isolated runner", DIM)
            _box(d, (c[6], y2, c[7], y2 + bh), "pass/fail", "wrong dies", GREEN)
            for x0, x1 in ((c[1], c[2]), (c[3], c[4]), (c[5], c[6])):
                _arrow(d, x0, y2 + bh // 2, x1)
            center_text(d, 840, "the agent never sees the tests — and can't shadow the check",
                        font(30), DIM)
        else:
            center_text(d, y2 + 40, "…", font(48), DIM)
        footer(d, 4)
        return img

    return [(draw(False), 0.45), (draw(True), 1.0)]


def scene5() -> list[tuple[Image.Image, float]]:
    """The reveal: phase 1 = evidence-only card vs a dim '?'; phase 2 = full gate."""
    def draw(full: bool) -> Image.Image:
        img, d = new_frame()
        center_text(d, 90, "measured, not asserted", font(48), TEXT)
        center_text(d, 160, "35-run labeled corpus · live Nebius Sandboxes · 2026-09-30",
                    font(26), DIM)
        y = 270
        bx = (TERM_X, y, TERM_X + 700, y + 380)
        d.rounded_rectangle(bx, radius=18, fill=PANEL, outline=BORDER, width=2)
        d.text((bx[0] + 34, y + 30), "evidence review alone", font=font(32), fill=DIM)
        d.text((bx[0] + 34, y + 110), "60%", font=font(120), fill=ORANGE)
        d.text((bx[0] + 34, y + 260), "sensitivity 3/5 — two defective runs",
               font=font(26, mono=True), fill=DIM)
        d.text((bx[0] + 34, y + 300), "looked green and slipped through",
               font=font(26, mono=True), fill=DIM)
        bx2 = (TERM_X + 820, y, TERM_X + TERM_W, y + 380)
        if full:
            d.rounded_rectangle(bx2, radius=18, fill=PANEL2, outline=GREEN, width=3)
            d.text((bx2[0] + 34, y + 30), "full gate: evidence + replay + oracle",
                   font=font(32), fill=GREEN)
            d.text((bx2[0] + 34, y + 110), "100%", font=font(120), fill=GREEN)
            d.text((bx2[0] + 34, y + 260), "sensitivity 5/5 · specificity 97% (29/30)",
                   font=font(26, mono=True), fill=TEXT)
            d.text((bx2[0] + 34, y + 300), "the one miss: contract impossible by design",
                   font=font(26, mono=True), fill=DIM)
            center_text(d, 720, "$ runanchor check — ok: 291 snapshots / 219 receipts, hash chain intact",
                        font(26, mono=True), CYAN)
            center_text(d, 780, "small sample — corpus, judge prompt and commands are in the repo",
                        font(24), DIM)
        else:
            d.rounded_rectangle(bx2, radius=18, outline=BORDER, width=2)
            tw, th = text_size(d, "?", font(120))
            d.text(((bx2[0] + bx2[2]) / 2 - tw / 2, y + 130), "?", font=font(120), fill=BORDER)
            d.text((bx2[0] + 34, y + 30), "+ replay + hidden oracle", font=font(32), fill=DIM)
        footer(d, 5)
        return img

    return [(draw(False), 0.35), (draw(True), 1.0)]


def scene6() -> list[tuple[Image.Image, float]]:
    img, d = new_frame()
    center_text(d, 90, "under the hood", font(48), TEXT)
    y = 270
    bw, gap = 280, 60
    x = TERM_X
    steps = [
        ("agent task", ["writes & runs code"], DIM),
        ("Nebius Sandboxes", ["ConTree microVM", "op + image UUIDs"], CYAN),
        ("receipt", ["provider-anchored", "fingerprints", "decision"], TEXT),
        ("verify", ["replay + oracle"], YELLOW),
        ("ledger", ["append-only", "hash-chained"], GREEN),
    ]
    for i, (t, subs, c) in enumerate(steps):
        _box(d, (x, y, x + bw, y + 180), t, None, c)
        for j, s in enumerate(subs):
            d.text((x + 26, y + 76 + j * 34), s, font=font(20, mono=True), fill=DIM)
        if i < len(steps) - 1:
            _arrow(d, x + bw, y + 90, x + bw + gap)
        x += bw + gap
    _box(d, (TERM_X, 600, TERM_X + 700, 740), "Nemotron planner", "nvidia/nemotron-3-super-120b-a12b · Token Factory", CYAN)
    _box(d, (TERM_X + 860, 600, TERM_X + TERM_W, 740), "Nemotron judge", "nvidia/Nemotron-3_5-Lightning · measurement", CYAN)
    center_text(d, 820, "pending → adopted / rejected · mismatch & unresolved — never deleted",
                font(26, mono=True), DIM)
    footer(d, 6)
    return [(img, 1.0)]


def scene7() -> list[tuple[Image.Image, float]]:
    img, d = new_frame()
    y = 300
    y = center_text(d, y, "runanchor", font(110, mono=True), TEXT, stroke=1) + 36
    y = center_text(d, y, "check our numbers, not our claims", font(42), CYAN) + 80
    y = center_text(d, y, "MIT · offline demo:  runanchor demo", font(30, mono=True), TEXT) + 10
    y = center_text(d, y, "github.com/tatsuya7899/runanchor", font(30, mono=True), DIM) + 70
    center_text(d, y, "Nebius × NVIDIA Global AI Hackathon — Coding & Agentic Engineering",
                font(26), DIM)
    footer(d, 7)
    return [(img, 1.0)]


SCENES = {1: scene1, 2: scene2, 3: scene3, 4: scene4, 5: scene5, 6: scene6, 7: scene7}


# ---------- audio ----------

def tts(text: str, out: Path) -> float:
    aiff = out.with_suffix(".aiff")
    subprocess.run(["say", "-v", "Samantha", "-r", "178", "-o", str(aiff), text],
                   check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff),
                    "-ar", "44100", "-ac", "2", str(out)], check=True)
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(out)], capture_output=True, text=True, check=True)
    return float(p.stdout.strip())


def pad_audio(src: Path, dur: float, out: Path) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                    "-af", "apad", "-t", f"{dur}", "-ar", "44100", "-ac", "2",
                    str(out)], check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default="/tmp/ra-video")
    ap.add_argument("--out", default=str(ROOT / "submit" / "runanchor-demo.mp4"))
    args = ap.parse_args()
    work = Path(args.workdir)
    frames_dir = work / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    # 1. TTS per scene → measure → scene durations
    scene_dur = {}
    tts_paths = {}
    for n, text in NARR.items():
        wav = work / f"tts-{n}.wav"
        d = tts(text, wav)
        scene_dur[n] = max(MIN_DUR[n], d + 1.2)
        tts_paths[n] = wav
        print(f"scene {n}: tts {d:.1f}s → scene {scene_dur[n]:.1f}s")

    # 2. render frames
    concat_lines = []
    idx = 0
    for n in sorted(SCENES):
        frames = SCENES[n]()
        total_w = sum(wt for _, wt in frames)
        for img, wt in frames:
            p = frames_dir / f"f{idx:04d}.png"
            img.save(p)
            concat_lines += [f"file '{p}'", f"duration {wt / total_w * scene_dur[n]:.3f}"]
            idx += 1
    concat_lines.append(f"file '{frames_dir / f'f{idx - 1:04d}.png'}'")  # demuxer tail
    concat = work / "frames.txt"
    concat.write_text("\n".join(concat_lines))
    total = sum(scene_dur.values())
    print(f"total {total:.1f}s · {idx} frames")

    # 3. video track (fade in/out)
    vonly = work / "video.mp4"
    fade_out_start = total - 0.6
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(concat), "-vf",
                    f"fps=30,format=yuv420p,fade=t=in:st=0:d=0.5,fade=t=out:st={fade_out_start:.2f}:d=0.6",
                    "-t", f"{total:.3f}",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(vonly)],
                   check=True)

    # 4. audio track: pad each tts to its scene length, concat
    alist = work / "audio.txt"
    with alist.open("w") as f:
        for n in sorted(SCENES):
            p = work / f"tts-{n}-pad.wav"
            pad_audio(tts_paths[n], scene_dur[n], p)
            f.write(f"file '{p}'\n")
    audio = work / "audio.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(alist), "-c", "copy", str(audio)], check=True)

    # 5. mux
    out = Path(args.out)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(vonly), "-i", str(audio),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
                    str(out)], check=True)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
