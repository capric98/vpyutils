#!/usr/local/env python3
# coding: utf-8
import argparse
import os
import subprocess
import shutil


__FFMPEG__ = shutil.which("ffmpeg")
__FFPROBE_ = shutil.which("ffprobe")


def _check_env():
    if not __FFMPEG__:
        print("ffmpeg not installed!")
        exit(1)
    if not __FFPROBE_:
        print("ffprobe not found!")
        exit(1)

def get_framerate(fn) -> tuple[int, int]:
    ex = subprocess.run([__FFPROBE_, "-v", "0", "-of", "csv=p=0", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", fn], capture_output=True)
    stderr = ex.stdout.decode("utf-8")
    numerator, denominator = stderr.strip().split("/")

    return (int(numerator), int(denominator))


if __name__=="__main__":
    _check_env()

    parser = argparse.ArgumentParser(
        prog="gif_generate.py",
        description="generate gif from video file",
        epilog="_(:з」∠)_",
    )

    parser.add_argument("video_fn", type=str)
    parser.add_argument("-r", "--fps", type=int, help="output fps", default=12)
    parser.add_argument("-w", "--width", type=int, help="loudness range", default=500)
    # parser.add_argument("-h", "--height", type=int, help="resize height", default=-2)
    parser.add_argument("-s", "--start", type=int, help="start frame", default=None)
    parser.add_argument("-e", "--end", type=int, help="end frame", default=None)
    parser.add_argument("-c", "--crop", type=bool, help="interactively input crop parameter", default=False)

    args = parser.parse_args()

    numerator, denominator = get_framerate(args.video_fn)
    fargs = [
        __FFMPEG__, "-hide_banner", "-loglevel", "info", "-nostats",
        "-i", args.video_fn, "-r", str(args.fps)
    ]

    if args.start: fargs += ["-ss", f"{(args.start+1)*denominator/numerator:.4f}"]
    if args.end: fargs += ["-t", f"{(args.end-args.start-1)*denominator/numerator:.4f}"]

    filter = ""
    if args.crop:
        w = input("output width: ").strip()
        h = input("output height: ").strip()
        x = input("left horizontal position: ").strip()
        y = input("top vertical position: ").strip()
        filter += f"crop={w}:{h}:{x}:{y},"

    filter += f"zscale={args.width}:-2:filter=spline36"
    filter += ",split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
    fargs  += ["-an", "-vf", filter]

    fargs += ["-loop", "0", "-y", os.path.splitext(args.video_fn)[0]+".gif"]

    subprocess.run(fargs, capture_output=True)