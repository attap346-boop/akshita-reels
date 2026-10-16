"""Builds one 9:16 reel (black background, white Hindi line, handle tag, soft music).

Usage: python3 make_reel.py --audio audio.wav [--date YYYY-MM-DD] [--out reels]
Writes <out>/<date>.mp4 and <out>/<date>.json (caption for the post).
"""
import argparse
import datetime
import json
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

HANDLE = "@akshita_writes1"
HASHTAGS = "#hindiquotes #hindilines #hindiwriting #akshitawrites"
W, H = 1080, 1920
DURATION = 8
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
EPOCH = datetime.date(2026, 1, 1)
HERE = os.path.dirname(os.path.abspath(__file__))


def find_font(bold=False):
    out = subprocess.run(["fc-list", ":lang=hi", "file"], capture_output=True, text=True).stdout
    paths = [l.split(":")[0].strip() for l in out.splitlines() if "FreeSans" in l]
    if not paths:
        paths = ["/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                 "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"]
    paths.sort(key=lambda p: ("Bold" in p) != bold)
    return paths[0]


def render_frame(text, path):
    img = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(img)
    lines = text.split("\n")
    size = 56
    while True:
        f_main = ImageFont.truetype(find_font(), size)
        widest = max((d.textlength(l, font=f_main) for l in lines if l), default=0)
        if widest <= W - 240 or size <= 36:
            break
        size -= 2
    gap, blank = int(size * 1.5), int(size * 0.85)
    block = sum(gap if l else blank for l in lines)
    x, y = 120, int(H * 0.47 - block / 2)
    for l in lines:
        if l:
            d.text((x, y), l, font=f_main, fill=(255, 255, 255))
        y += gap if l else blank
    f_handle = ImageFont.truetype(find_font(bold=True), 32)
    d.text((x - 6, y + 24), HANDLE, font=f_handle, fill=(170, 170, 170))
    img.save(path)


def audio_start(audio, idx):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", audio],
        capture_output=True, text=True).stdout.strip()
    dur = float(out or 0)
    room = int(dur) - (DURATION + 4)
    return (idx * 37) % room if room > 0 else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--date")
    ap.add_argument("--out", default="reels")
    a = ap.parse_args()

    date = datetime.date.fromisoformat(a.date) if a.date else datetime.datetime.now(IST).date()
    lines = json.load(open(os.path.join(HERE, "lines.json"), encoding="utf-8"))
    idx = (date - EPOCH).days
    text = lines[idx % len(lines)]

    os.makedirs(a.out, exist_ok=True)
    frame = os.path.join(a.out, f".frame-{date}.png")
    mp4 = os.path.join(a.out, f"{date}.mp4")
    render_frame(text, frame)

    start = audio_start(a.audio, idx)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-framerate", "30", "-i", frame,
        "-ss", str(start), "-i", a.audio, "-t", str(DURATION),
        "-vf", "fade=t=in:st=0:d=1.2,format=yuv420p",
        "-af", f"afade=t=in:st=0:d=1,afade=t=out:st={DURATION - 1.5}:d=1.5,volume=0.8",
        "-c:v", "libx264", "-r", "30", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart", mp4,
    ], check=True)
    os.remove(frame)

    caption = text.replace("\n\n", "\n").replace("\n", " ") + "\n\n" + HASHTAGS
    with open(os.path.join(a.out, f"{date}.json"), "w", encoding="utf-8") as f:
        json.dump({"date": str(date), "caption": caption, "line": text}, f, ensure_ascii=False)
    print("built", mp4, "audio start", start)


if __name__ == "__main__":
    main()
