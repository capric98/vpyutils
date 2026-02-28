#!/usr/bin/env python3
# coding: utf-8
import argparse
import json
import os
import re
import shutil
import subprocess


__FFMPEG__ = shutil.which("ffmpeg")


def _check_env():
    if not __FFMPEG__:
        print("ffmpeg not installed!")
        exit(1)

def loudnorm(input_fn, output_fn, args):
    print(f"Processing \"{input_fn}\"...")

    ex = subprocess.run([
        __FFMPEG__, "-hide_banner", "-loglevel", "info", "-nostats",
        "-i", input_fn,
        "-vn", "-af", "loudnorm=print_format=json", "-f", "null", output_fn,
    ], capture_output=True)

    stderr = ex.stderr.decode("utf-8", errors="ignore")
    # print(stderr)
    r = re.search(r"\[Parsed_loudnorm.*?\}", stderr, re.DOTALL)
    r = re.search(r"{.*}", r.group(0), re.DOTALL)
    # print("<=====================================>")
    # print(r.group(0))
    if not r:
        print("ffmpeg gives unexpected output as:")
        for line in stderr.splitlines(): print(f" > {line}")
        return
    else:
        measure = json.loads(r.group(0))
        # print(measure)

        mi      = measure["input_i"]
        mlra    = measure["input_lra"]
        mtp     = measure["input_tp"]
        mthresh = measure["input_thresh"]

        fargs = [
            __FFMPEG__, "-hide_banner", "-loglevel", "info", "-nostats",
            "-i", input_fn, "-map", "0",
            "-af", f"loudnorm=I={args.LUFS}:LRA={mlra}:TP={args.TP}:measured_I={mi}:measured_LRA={mlra}:measured_TP={mtp}:measured_thresh={mthresh}",
        ]
        fargs += ["-vn"] if args.no_video else ["-c:v", "copy"]
        fargs += ["-c:s", "copy", "-c:a", args.encoder]
        if args.bitrate: fargs += ["-ab", args.bitrate]
        if args.sample: fargs += ["-ar", args.sample]

        print(fargs)
        subprocess.run(fargs + ["-y", output_fn], capture_output=True)


if __name__=="__main__":
    _check_env()

    parser = argparse.ArgumentParser(
        prog="loudnorm.py",
        description="loudness normalization",
        epilog="_(:з」∠)_",
    )

    parser.add_argument("video_fn", type=str, nargs="+")
    parser.add_argument("-i", "--LUFS", type=float, help="loudness target", default=-18.0)
    parser.add_argument("-t", "--TP", type=float, help="true peak loudness", default=-1.0)
    parser.add_argument("-e", "--encoder", type=str, help="audio encoder", default="aac")
    parser.add_argument("-r", "--sample", type=str, help="audio sample rate", default="44100")
    parser.add_argument("-b", "--bitrate", type=str, help="audio bitrates", default=None)
    parser.add_argument("-vn", "--no-video", dest="no_video", help="audio only", default=False, action="store_true")

    # parser.add_argument("--category", type=str, help="torrent catagory", default="")

    args = parser.parse_args()
    if args.encoder=="aac" and not args.bitrate: args.bitrate="320k"


    for fn in args.video_fn:
        if os.path.isfile(fn):
            ps = os.path.splitext(fn)
            loudnorm(fn, ps[0]+".norm"+ps[1], args)
        elif os.path.isdir(fn):
            pn = fn
            for sfn in os.listdir(pn):
                fn = os.path.join(pn, sfn)
                if os.path.isfile(fn):
                    ps = os.path.splitext(fn)
                    loudnorm(fn, ps[0]+".norm"+ps[1], args)
