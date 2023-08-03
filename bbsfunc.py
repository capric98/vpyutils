# coding: utf-8
# prerequisites:
#   Python >= 3.10
#   VapourSynth >= R58
#   Plugins: xxx
#   Scripts: xxx

import os

from datetime import timedelta
from math import ceil

import vapoursynth as vs


class EditPoint():
    def __init__(self, point: timedelta | int) -> None:
        if isinstance(point, timedelta) or isinstance(point, int):
            self.value = point
        else:
            raise ValueError("EditPoint can only be timedelta or frame number")

    def __eq__(self, other):
        return self.value==other

    def calc_framenum(self, video: vs.VideoNode) -> int:
        if isinstance(self.value, int):
            return self.value
        else:
            numerator = video.fps.numerator
            denominator = video.fps.denominator

            if numerator==0 and denominator==0:
                raise ZeroDivisionError("cannot calc exact frame number from a variable framerate VideoNode")

            return ceil(self.value.total_seconds() * numerator / denominator)


class BBNode():
    def __init__(self, video: vs.VideoNode, audio: vs.AudioNode|None = None) -> None:
        self.video = video
        self.audio = audio

    # Act like a vs.VideoNode.
    def __getattr__(self, name: str) -> any:
        return getattr(self.video, name)

    def trim(self, start: EditPoint, end: EditPoint = EditPoint(0), length: EditPoint = EditPoint(0)) -> None:
        if end==0 and length==0:
            raise ValueError("trim needs an end or length parameter")
        else:
            first  = start.calc_framenum(self.video)
            last   = end.calc_framenum(self.video)
            length = length.calc_framenum(self.video)

            if last!=0:
                self.video = self.video.std.Trim(first=first, last=last)
                if self.audio is not None:
                    self.audio = self.audio.std.AudioTrim(first=first, last=last)
            else:
                self.video = self.video.std.Trim(first=first, length=length)
                if self.audio is not None:
                    self.audio = self.audio.std.AudioTrim(first=first, length=length)


def source(file: os.PathLike) -> BBNode:

    core  = vs.core

    video = core.ffms2.Source(file)
    audio = None

    try:
        audio = core.bas.Source(file, track=-1)
    except Exception as e:
        print(f"warning: failed to load audio source with \"{e}\"")

    return BBNode(video, audio)



def deinterlace(clip: vs.VideoNode, divide: bool = True, TFF: bool = True, preset: str = "Fast", blur: bool = False) -> vs.VideoNode:
    """
    preset: "Placebo", "Very Slow", "Slower", "Slow", "Medium", "Fast", "Faster", "Very Fast", "Super Fast", "Ultra Fast", "Draft"
    """
    import havsfunc as haf
    if divide:
        if blur:
            clip = haf.QTGMC(Input=clip, Preset=preset, TFF=TFF, FPSDivisor=2, ShutterBlur=2)
        else: clip = haf.QTGMC(Input=clip, Preset=preset, TFF=TFF, FPSDivisor=2)
    else: clip = haf.QTGMC(Input=clip, Preset=preset, TFF=TFF)
    return clip


def IVTC(clip: vs.VideoNode) -> vs.VideoNode:
    import mvsfunc  as mvf
    import havsfunc as haf
    core = vs.core

    if clip.format.color_family is not vs.ColorFamily.YUV:
        if clip.format.subsampling_w + clip.format.subsampling_h:
            clip = core.fmtc.resample(clip=clip, css="444")
        clip = core.fmtc.matrix(clip=clip, col_fam=vs.ColorFamily.YUV, matd="709")

    if clip.format.bits_per_sample != 8:
        clip = core.fmtc.bitdepth(clip, bits=8, dmode=1) # no dither

    return mvf.FilterCombed(core.vivtc.VFM(clip, order=0, mode=5, cthresh=6, mi=64),
        haf.QTGMC(clip, TFF=True, FPSDivisor=2, Preset="slow", FftThreads=8)).vivtc.VDecimate()


def deband(clip: vs.VideoNode) -> vs.VideoNode:
    import mvsfunc as mvf
    core = vs.core

    pass1 = core.neo_f3kdb.Deband(clip,  8, 48, 48, 48, 0, 0, output_depth=16)
    pass2 = core.neo_f3kdb.Deband(pass1,16, 32, 32, 32, 0, 0, output_depth=16)
    return mvf.LimitFilter(pass2, clip, thr=0.4, thrc=0.3, elast=3.0)


def subtitle(clip: vs.VideoNode, file: str, accurate: bool = False) -> vs.VideoNode:
    """
    clip: VapourSynth VideoNode
    file: subtitle file path
    (optional) accurate: True/False(default)
        True -> enable accurate render for 10/16bit(~2x slower)
    The output format may be different from input if the input was not
    in [YUV420P8, YUV420P10, YUV420P16, RGB24].
    """

    core = vs.core

    if clip.format.name not in ["YUV420P8", "YUV420P10", "YUV420P16", "RGB24"]:
        if clip.format.color_family is not vs.ColorFamily.YUV:
            # covert to YUV420P16
            # fmtc.matrix can only process 4:4:4
            if clip.format.subsampling_w + clip.format.subsampling_h:
                clip = core.fmtc.resample(clip=clip, css="444")
            clip = core.fmtc.matrix(clip=clip, col_fam=vs.ColorFamily.YUV, matd="709")
            clip = core.fmtc.resample(clip=clip, css="420")
        else:
            # resample to YUV420Px
            clip = core.fmtc.resample(clip=clip, css="420")

    return core.vsfm.TextSubMod(clip=clip, file=file, accurate=int(accurate))


def eedi3_rpow2(clip: vs.VideoNode) -> vs.VideoNode:
    core = vs.core
    clip = core.eedi3m.EEDI3(clip, field=1, dh=True).std.Transpose()
    clip = core.eedi3m.EEDI3(clip, field=1, dh=True).std.Transpose()
    return clip
def eedi2_rpow2(clip: vs.VideoNode) -> vs.VideoNode:
    core = vs.core
    clip = core.eedi2.EEDI2(clip, field=1, mthresh=10, lthresh=20, vthresh=20, maxd=24, nt=50).std.Transpose()
    clip = core.eedi2.EEDI2(clip, field=1, mthresh=10, lthresh=20, vthresh=20, maxd=24, nt=50).std.Transpose()
    return clip
def eedin_resize(clip, width, height, rpow2_func=eedi3_rpow2) -> vs.VideoNode:
    clipx2 = rpow2_func(clip)
    return clipx2.fmtc.resample(width, height, kernel="spline64")


def set_output(clip: vs.VideoNode, depth: int = 8, index: int = 0):
    """
    set output
    """
    import mvsfunc as mvf
    core = vs.core

    if clip.format.color_family is not vs.ColorFamily.YUV:
        # covert to YUV420P16
        # fmtc.matrix can only process 4:4:4
        if clip.format.subsampling_w + clip.format.subsampling_h:
            clip = core.fmtc.resample(clip=clip, css="444")
        clip = core.fmtc.matrix(clip=clip, col_fam=vs.ColorFamily.YUV, matd="709")
        clip = core.fmtc.resample(clip=clip, css="420")

    # if clip.format.bits_per_sample != depth:
    #     clip = core.fmtc.bitdepth(clip, bits=depth, dmode=0)

    if "YUV420" not in clip.format.name:
        clip = core.fmtc.resample(clip=clip, css="420")

    if clip.format.bits_per_sample > depth:
        # bright = mvf.Depth(clip , depth=depth, dither=0, ampo=0.5)
        bright = mvf.Depth(clip , depth=depth, dither=1)
        dark   = mvf.Depth(clip , depth=depth, dither=0, ampo=2)
        clip = core.std.MaskedMerge(dark, bright, core.std.Binarize(bright, 100, planes=0), first_plane=True)

    clip.set_output(index)


if __name__ == "__main__":
    pass