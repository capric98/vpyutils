# coding: utf-8
import vapoursynth as vs
import mvsfunc as mvf

core = vs.core

def mts(src):
    src8 = mvf.ToYUV(src, css='420')
    src16 = core.fmtc.bitdepth(src8,bits=16)

    # Denoise
    src_rgb = mvf.ToRGB(src16,depth=32)
    #nr16_rgb = core.pdn.BM3DBasic(src_rgb, sigma=[0.5, 0.2, 0.2],group_size=16, bm_range=8)
    nr16_rgb = core.pdn.BM3DBasic(src_rgb, sigma=[1.0, 0.5, 0.5])
    nr16 = mvf.ToYUV(nr16_rgb, css="420",depth=16)
    noise16 = core.std.MakeDiff(src16, nr16)

    # Mask
    pre16 = core.std.ShufflePlanes([nr16,src16],[0,1,2],vs.YUV)
    pre8 = mvf.Depth(pre16, depth=8, dither=5)

    eemask = core.tcanny.TCanny(pre8,sigma=0.6,op=2,gmmax=255,planes=[0,1,2],mode=1)
    eemask_u = core.std.ShufflePlanes(eemask, [1,1,1], vs.YUV).fmtc.resample(1920,1080,sx=0.25,css="420")
    eemask_v = core.std.ShufflePlanes(eemask, [2,2,2], vs.YUV).fmtc.resample(1920,1080,sx=0.25,css="420")
    weighted = core.std.Expr([eemask,eemask_u,eemask_v],["x 64 * y + z +",""],vs.YUV420P16)

    luma = core.std.ShufflePlanes(pre8, 0, vs.YUV).resize.Bilinear(format=vs.YUV420P8)
    eemask = core.std.Expr([eemask,luma],["x x * 20 * 255 y - dup * 0.2 * + 50000 min","x x * 30 * 255 y - dup * 0.3 * + 60000 min"],vs.YUV420P16)
    eemask = core.std.Maximum(eemask,planes=[0,1,2])
    eemask = core.rgvs.RemoveGrain(eemask, [20,11]).rgvs.RemoveGrain([20,11]).rgvs.RemoveGrain([20,11])

    aamask = core.std.Binarize(weighted, 12000, 0)

    nrmasks = core.std.Binarize(weighted, 4500, 0)

    dmaskb = core.std.Binarize(weighted, 3000, 0)
    dmaskm = core.std.Binarize(weighted, 3500, 0)
    dmasks = core.std.Binarize(weighted, 3800, 0)
    dmask_dark = core.misc.Hysteresis(dmaskm, dmaskb)
    dmask_bright = core.misc.Hysteresis(dmasks, dmaskm)
    dmask = core.std.Expr([src16, dmask_dark, dmask_bright], "x 24672 < y z ?")

    nrmaskg = core.tcanny.TCanny(pre8,sigma=1.5,t_l=8,t_h=15,op=2,planes=0)
    nrmaskb = core.tcanny.TCanny(pre8,sigma=1.2,t_l=8,t_h=11,op=2,planes=0)

    nrmask = core.std.Expr([nrmaskg,nrmaskb,nrmasks,pre8,dmask],["a 20 < 65535 a 64 < x 257 * b max a 160 < y 257 * z ? ? ?","",""],vs.YUV420P16)
    nrmask = core.std.Maximum(nrmask,0).std.Maximum(0).std.Minimum(0).std.Minimum(0)
    nrmask = core.rgvs.RemoveGrain(core.rgvs.RemoveGrain(nrmask,[20,0]),[20,0])


    Y = core.std.ShufflePlanes(src16, 0, vs.YUV).resize.Bicubic(1920, 1080, format=vs.YUV420P16, filter_param_a=0, filter_param_b=0.5)
    U = core.std.ShufflePlanes(src16, [1,1,1], vs.YUV).resize.Bicubic(1920, 1080, format=vs.YUV420P16, filter_param_a=0, filter_param_b=0.5)
    V = core.std.ShufflePlanes(src16, [2,2,2], vs.YUV).resize.Bicubic(1920, 1080, format=vs.YUV420P16, filter_param_a=0, filter_param_b=0.5)
    textmask0 = core.std.Expr([Y,U,V], ["x 60000 > y 32768 - abs 768 < and z 32768 - abs 768 < and 65535 0 ?","0"])
    #textmasks = core.std.Expr([Y,U,V], ["x 58000 > y 32768 - abs 512 < and z 32768 - abs 512 < and 65535 0 ?","0"])
    textmask1 = core.std.Minimum(textmask0, 0).std.Minimum(planes=0).std.Minimum(planes=0).std.Maximum(0).std.Maximum(0).std.Maximum(0)
    textmask2 = core.misc.Hysteresis(textmask1, textmask0, planes=0)
    textmask = core.std.Expr([textmask0, textmask2], "x y > x 0 ?")
    #textmask = core.misc.Hysteresis(textmasks, textmaskb, planes=0)
    textmask = core.std.Maximum(textmask,0).std.Maximum(0).std.Maximum(0)#.std.Maximum(0)#.std.Maximum(0)#.std.Maximum(0)#.std.Minimum(0)

    debd = core.f3kdb.Deband(nr16,8,48,32,32,0,0,output_depth=16)
    debd = core.f3kdb.Deband(debd,15,32,24,24,0,0,output_depth=16)
    debd = mvf.LimitFilter(debd,nr16,thr=0.7,thrc=0.5,elast=2.0)
    debd = core.std.MaskedMerge(debd, nr16, nrmask, first_plane=1)

    w  = 1920
    h  = 1080
    oaa_y = core.std.ShufflePlanes(nr16, 0, vs.GRAY)

    aa_y = core.eedi2.EEDI2(oaa_y,field=1,mthresh=10,lthresh=20,vthresh=20,maxd=24,nt=50).fmtc.resample(w,h,sy=-0.5, kernel='bicubic', a1=0, a2=0.5,).std.Transpose()
    aa_y = core.eedi2.EEDI2(aa_y,field=1,mthresh=10,lthresh=20,vthresh=20,maxd=24,nt=50).fmtc.resample(h,w,sy=-0.5, kernel='bicubic', a1=0, a2=0.5,).std.Transpose()

    aa_clip = core.std.ShufflePlanes([aa_y,nr16], [0,1,2], vs.YUV)
    aaed = core.std.MaskedMerge(debd, aa_clip, aamask, 0, True)
    aaed = core.std.MaskedMerge(aaed, debd, textmask, 0, False)

    dif = core.std.MakeDiff(aaed, core.rgvs.RemoveGrain(aaed,20))
    sharp = core.std.MergeDiff(aaed, dif)
    sharped = core.std.MaskedMerge(sharp, aaed, eemask, [0,1,2], False)

    noise16 = core.std.Expr(noise16,["x 32768 - 1.05 * 32768 +",""])
    nullclip = core.std.Expr(src16,["32768",""])
    nrweight = core.std.Expr(pre8, ["x 48 - 0 max dup * 5 * ",""], vs.YUV420P16)
    noise16 = core.std.MaskedMerge(noise16,nullclip,nrweight,0,True)
    res = core.std.MergeDiff(sharped,noise16,0)

    return res

def camp(src):
    src16 = core.fmtc.bitdepth(src, bits=16)

    src_rgb = mvf.ToRGB(src16,depth=32)
    nr16_rgb = core.pdn.BM3DBasic(src_rgb, sigma=[0.5, 0.2, 0.2])
    nr16 = mvf.ToYUV(nr16_rgb, css="420",depth=16)
    noise16 = core.std.MakeDiff(src16, nr16)

    pre16 = core.std.ShufflePlanes([nr16,src16],[0,1,2],vs.YUV)
    pre8 = mvf.Depth(pre16, depth=8, dither=5)

    eemask = core.tcanny.TCanny(pre8,sigma=0.6,op=2,gmmax=255,planes=[0,1,2],mode=1)
    eemask_u = core.std.ShufflePlanes(eemask, [1,1,1], vs.YUV).fmtc.resample(1920,1080,sx=0.25,css="420")
    eemask_v = core.std.ShufflePlanes(eemask, [2,2,2], vs.YUV).fmtc.resample(1920,1080,sx=0.25,css="420")
    weighted = core.std.Expr([eemask,eemask_u,eemask_v],["x 64 * y + z +",""],vs.YUV420P16)

    luma = core.std.ShufflePlanes(pre8, 0, vs.YUV).resize.Bilinear(format=vs.YUV420P8)
    eemask = core.std.Expr([eemask,luma],["x x * 20 * 255 y - dup * 0.2 * + 50000 min","x x * 30 * 255 y - dup * 0.3 * + 60000 min"],vs.YUV420P16)
    eemask = core.std.Maximum(eemask,planes=[0,1,2])
    eemask = core.rgvs.RemoveGrain(eemask, [20,11]).rgvs.RemoveGrain([20,11]).rgvs.RemoveGrain([20,11])

    aamask = core.std.Binarize(weighted, 8000, 0)
    Y = core.std.ShufflePlanes(src16, 0, vs.YUV).resize.Bicubic(1920, 1080, format=vs.YUV420P16, filter_param_a=0, filter_param_b=0.5)
    U = core.std.ShufflePlanes(src16, [1,1,1], vs.YUV).resize.Bicubic(1920, 1080, format=vs.YUV420P16, filter_param_a=0, filter_param_b=0.5)
    V = core.std.ShufflePlanes(src16, [2,2,2], vs.YUV).resize.Bicubic(1920, 1080, format=vs.YUV420P16, filter_param_a=0, filter_param_b=0.5)
    textmask0 = core.std.Expr([Y,U,V], ["x 60000 > y 32768 - abs 768 < and z 32768 - abs 768 < and 65535 0 ?","0"])
    #textmasks = core.std.Expr([Y,U,V], ["x 58000 > y 32768 - abs 512 < and z 32768 - abs 512 < and 65535 0 ?","0"])
    textmask1 = core.std.Minimum(textmask0, 0).std.Minimum(planes=0).std.Minimum(planes=0).std.Maximum(0).std.Maximum(0).std.Maximum(0)
    textmask2 = core.misc.Hysteresis(textmask1, textmask0, planes=0)
    textmask = core.std.Expr([textmask0, textmask2], "x y > x 0 ?")
    #textmask = core.misc.Hysteresis(textmasks, textmaskb, planes=0)
    textmask = core.std.Maximum(textmask,0).std.Maximum(0).std.Maximum(0)#.std.Maximum(0)#.std.Maximum(0)#.std.Maximum(0)#.std.Minimum(0)

    debd = bbf.deband_2pass(nr16)

    w  = 1920
    h  = 1080
    oaa_y = core.std.ShufflePlanes(nr16, 0, vs.GRAY)

    aa_y = core.eedi2.EEDI2(oaa_y,field=1,mthresh=10,lthresh=20,vthresh=20,maxd=24,nt=50).fmtc.resample(w,h,sy=-0.5, kernel='bicubic', a1=0, a2=0.5,).std.Transpose()
    aa_y = core.eedi2.EEDI2(aa_y,field=1,mthresh=10,lthresh=20,vthresh=20,maxd=24,nt=50).fmtc.resample(h,w,sy=-0.5, kernel='bicubic', a1=0, a2=0.5,).std.Transpose()

    aa_clip = core.std.ShufflePlanes([aa_y,debd], [0,1,2], vs.YUV)
    aaed = core.std.MaskedMerge(debd, aa_clip, aamask, 0, True)
    aaed = core.std.MaskedMerge(aaed, debd, textmask, 0, False)

    dif = core.std.MakeDiff(aaed, core.rgvs.RemoveGrain(aaed,20))
    sharp = core.std.MergeDiff(aaed, dif)
    sharped = core.std.MaskedMerge(sharp, aaed, eemask, [0,1,2], False)

    noise16 = core.std.Expr(noise16,["x 32768 - 1.05 * 32768 +",""])
    nullclip = core.std.Expr(src16,["32768",""])
    nrweight = core.std.Expr(pre8, ["x 48 - 0 max dup * 5 * ",""], vs.YUV420P16)
    noise16 = core.std.MaskedMerge(noise16,nullclip,nrweight,0,True)
    res = core.std.MergeDiff(sharped,noise16,0)

    return res