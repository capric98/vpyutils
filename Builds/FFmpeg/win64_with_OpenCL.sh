#!/bin/bash
# For non-cross-compiled version, see https://github.com/m-ab-s/media-autobuild_suite

EXVERSION=ffmpeg-windows-build-helpers_withOpenCL

# gendef command for OpenCL$bits_target.def
apt-get install -y mingw-w64-tools

git clone https://github.com/rdp/ffmpeg-windows-build-helpers.git
mv ffmpeg-windows-build-helpers /opt/ffmpeg
cd /opt/ffmpeg

script_name=cross_compile_ffmpeg.sh

# TODO remove external link
# OpenCL.dll from Windows 10 Pro 20H2(19042.844)
wget https://file.io/hOgtlGBDBDKl -O patches/OpenCL64.dll

sed -i "s/--extra-version=ffmpeg-windows-build-helpers/--extra-version=${EXVERSION}/g" ${script_name}
sed -i "/build_nv_headers()/i # Thanks https:\/\/github.com\/rdp\/ffmpeg-windows-build-helpers\/issues\/183\#issuecomment-324818289" ${script_name}
sed -i "/build_nv_headers()/i build_opencl() {" ${script_name}
sed -i "/build_nv_headers()/i \ \ rm -rf OpenCL" ${script_name}
sed -i "/build_nv_headers()/i \ \ do_git_checkout https://github.com/KhronosGroup/OpenCL-Headers.git OpenCL" ${script_name}
sed -i "/build_nv_headers()/i \ \ cd OpenCL" ${script_name}
sed -i "/build_nv_headers()/i \ \ mkdir -p \$mingw_w64_x86_64_prefix/include/CL" ${script_name}
sed -i "/build_nv_headers()/i \ \ rm -f \$mingw_w64_x86_64_prefix/include/CL/*" ${script_name}
sed -i "/build_nv_headers()/i \ \ cp -vf CL/*.h \$mingw_w64_x86_64_prefix/include/CL/" ${script_name}
sed -i "/build_nv_headers()/i \ \ gendef \$(pwd)/../../../patches/OpenCL\$bits_target.dll" ${script_name}
sed -i "/build_nv_headers()/i \ \ \$mingw_w64_x86_64_prefix/bin/dlltool -l libOpenCL.a -d OpenCL\$bits_target.def -k -A" ${script_name}
sed -i "/build_nv_headers()/i \ \ cp -vf libOpenCL.a \$mingw_w64_x86_64_prefix/lib" ${script_name}
sed -i "/build_nv_headers()/i \ \ cd .." ${script_name}
sed -i "/build_nv_headers()/i }\n" ${script_name}

sed -i "/build_nv_headers$/a build_opencl" ${script_name}
sed -i "s/--enable-opengl/--enable-opencl --enable-opengl/g" ${script_name}

./${script_name} \
  --ffmpeg-git-checkout-version=n4.3.2 \
  --x265-git-checkout-version=Release_3.5 \
  --fdk-aac-git-checkout-version=v2.0.1 \
  --gcc-cpu-count=$(nproc) \
  --disable-nonfree=n \
  --build-lsw=y \
  --compiler-flavors=win64 \
  --prefer-stable=y \
  --enable-gpl=y
