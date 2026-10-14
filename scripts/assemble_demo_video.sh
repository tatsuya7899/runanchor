#!/bin/bash
# assemble_demo_video.sh — build submit/runanchor-demo.mp4 from the window
# capture produced by scripts/record_demo_capture.sh +
# capture_terminal_window.swift.
#
# Expects (working dir = $RA_CAPTURE_DIR, default /tmp/ra-capture):
#   win.mov            — ScreenCaptureKit window capture (VFR!)
#   sections.log       — epoch marks from the capture driver
#   aud/narration.m4a  — owner narration (concat of narration-1..7.mp3)
#   subtitle.txt       — title-card subtitle line
#
# NOTE: the SCK capture is variable-frame-rate — frames only exist while the
# screen changes. It is first densified to CFR 30fps (win30.mp4); tpad(frames)
# BEFORE setpts holds the last frame when a scene runs short of its narration
# budget.
set -e
RA="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${RA_CAPTURE_DIR:-/tmp/ra-capture}"
cd "$WORK"

CAP=win30.mp4
SCALE="scale=1920:1080,setsar=1"
mkdir -p seg

[ -f "$CAP" ] || ffmpeg -v error -y -i win.mov -vf "fps=30" \
  -c:v libx264 -crf 18 -preset fast -an "$CAP"

seg() { # $1 out  $2 src_start  $3 src_end(exclusive)  $4 setpts_factor  $5 target_dur
  local int padf
  int=$(python3 -c "print($3-$2)")
  padf=$(python3 -c "import math; print(math.ceil($5*30)+30)")
  ffmpeg -v error -y -ss "$2" -t "$int" -i "$CAP" \
    -vf "$SCALE,tpad=stop=$padf:stop_mode=clone,setpts=$4*PTS" \
    -t "$5" -an -r 30 "seg/$1.mp4"
}

# Section boundaries measured from sections.log vs the capture timeline
# (see submit/demo-script.md; values below are for the 2026-10-14 take).
seg s1 0.3 8.1 1.28 10.0
ffmpeg -v error -y -i seg/s1.mp4 -vf "\
drawtext=text='runanchor':fontfile=/System/Library/Fonts/SFNS.ttf:fontsize=96:fontcolor=white:x=(w-text_w)/2:y=h*0.38:enable='between(t,0,7)',\
drawtext=textfile=subtitle.txt:fontfile=/System/Library/Fonts/SFNS.ttf:fontsize=44:fontcolor=0x8B949E:x=(w-text_w)/2:y=h*0.38+120:enable='between(t,0,7)'" \
  -an -r 30 seg/s1t.mp4 && mv seg/s1t.mp4 seg/s1.mp4

seg s2 8.1 16.4 1.40 14.3
seg s3 16.5 26.3 1.20 11.8
seg s4 26.6 42.4 1.32 20.8
seg s5 43.5 58.3 1.47 21.8

ffmpeg -v error -y -loop 1 -i "$RA/submit/gallery-architecture.png" \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0D1117,zoompan=z='1+0.0006*on':d=435:s=1920x1080" \
  -t 14.5 -an -r 30 seg/s6.mp4

ffmpeg -v error -y -f lavfi -i "color=c=0x0D1117:s=1920x1080:d=7.9:r=30" -vf "\
drawtext=text='runanchor — MIT licensed':fontfile=/System/Library/Fonts/SFNS.ttf:fontsize=56:fontcolor=white:x=(w-text_w)/2:y=h*0.36,\
drawtext=text='github.com/tatsuya7899/runanchor':fontfile=/System/Library/Fonts/SFNSMono.ttf:fontsize=40:fontcolor=0x79C0FF:x=(w-text_w)/2:y=h*0.36+100,\
drawtext=text='runanchor demo — offline, no credentials':fontfile=/System/Library/Fonts/SFNS.ttf:fontsize=32:fontcolor=0x8B949E:x=(w-text_w)/2:y=h*0.36+180,\
drawtext=text='Nebius × NVIDIA Global AI Hackathon':fontfile=/System/Library/Fonts/SFNS.ttf:fontsize=28:fontcolor=0x8B949E:x=(w-text_w)/2:y=h*0.36+640" \
  -an seg/s7.mp4

printf "file 's1.mp4'\nfile 's2.mp4'\nfile 's3.mp4'\nfile 's4.mp4'\nfile 's5.mp4'\nfile 's6.mp4'\nfile 's7.mp4'\n" > seg/list.txt
ffmpeg -v error -y -f concat -safe 0 -i seg/list.txt -c copy seg/video.mp4
ffmpeg -v error -y -i seg/video.mp4 -i aud/narration.m4a -c:v copy -c:a copy -shortest final.mp4
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 final.mp4
echo "ASSEMBLE-OK — check, then: cp final.mp4 $RA/submit/runanchor-demo.mp4"
