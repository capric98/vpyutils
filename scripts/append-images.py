#!/usr/bin/env python3
# coding: utf-8
import argparse
import os
import uuid

from PIL import Image

img_extens = [
    ".bmp", ".dds", ".dib", ".eps", ".gif", ".icns", ".ico", ".im", ".jpeg", ".jpg",
    ".msp", ".pcx", ".png", ".ppm", ".sgi", ".spider", ".tga", ".tiff", ".webp", ".xbm",
]

def uniform(plist: list[Image.Image], vert: bool) -> list[Image.Image]:
    maxsize = -1
    pos = 0 if vert else 1

    for p in plist:
        maxsize = maxsize if maxsize>(p.size[pos]) else p.size[pos]

    if maxsize%2: maxsize += 1

    nplist = []
    for p in plist:
        if vert:
            tmp = int(round(
                (maxsize/p.size[0])*p.size[1]
            ))
            if tmp%2: tmp += 1
            newsize = (maxsize, tmp)
        else:
            tmp = int(round(
                (maxsize/p.size[1])*p.size[0]
            ))
            if tmp%2: tmp += 1
            newsize = (tmp, maxsize)

        p = p.resize(newsize, Image.Resampling.LANCZOS)
        nplist.append(p)

    return nplist

def pappend(pflist: list[os.PathLike], output: os.PathLike, vert: bool):
    if not output: output = "{}.png".format(uuid.uuid4())
    if not output.lower().endswith(".png"):
        output = "{}.png".format(os.path.splitext(file)[0])

    plist = uniform([Image.open(f) for f in pflist], vert)

    offset = 0
    if vert:
        op = Image.new("RGBA", (plist[0].size[0], sum([p.size[1] for p in plist])))
        for p in plist:
            op.paste(p, (0, offset))
            offset += p.size[1]
    else:
        op = Image.new("RGBA", (sum([p.size[0] for p in plist]), plist[0].size[1]))
        for p in plist:
            op.paste(p, (offset, 0))
            offset += p.size[0]

    op.save(output)

def from_list(file: os.PathLike, output: os.PathLike, vert: bool):
    plist = []
    with open(file) as f:
        for line in f.readlines():
            plist.append(line.strip())

    pappend(plist, output, vert)

def pil_readable(file: os.PathLike) -> bool:
    _, ext = os.path.splitext(file)
    ext = str(ext).lower()
    return ext in img_extens

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Append Images")
    parser.add_argument("--horizontal", "-H", action=argparse.BooleanOptionalAction, help="horizontal direction(vertical if not specify)")
    parser.add_argument("--output", "-O", help="output file")
    parser.add_argument("files", type=str, nargs="*", help="force files")

    args = parser.parse_args()

    plist = []
    for file in args.files:
        if file.lower().endswith(".txt"):
            from_list(file, args.output, (not args.horizontal))
        elif pil_readable(file):
            plist.append(file)

    if plist: pappend(plist, args.output, (not args.horizontal))

    pass