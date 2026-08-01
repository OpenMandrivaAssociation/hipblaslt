# hipBLASLt — GEMM with TensileLite (RDNA3/4 + CDNA; no gfx803)
# Device generation uses system origami, stinkytofu, and python-rocisa.

Name:		hipblaslt
Version:	7.14.0
Release:	2
%{!?rocm_llvm_maj_ver:%global rocm_llvm_maj_ver 23}
Summary:	HIP BLAS library with lightweight Tensile GEMM kernels
License:	MIT
Group:		System/Libraries
URL:		https://github.com/ROCm/rocm-libraries
Source0:	https://github.com/ROCm/rocm-libraries/releases/download/therock-7.14/hipblaslt.tar.gz#/hipblaslt-%{version}.tar.gz
# Use system rocisa: keep tensilelite pure-Python on PYTHONPATH when BUNDLE=OFF
Patch0:		0002-system-deps-find-package.patch
# LLVM 23 true16: f16 convert dst needs .l/.h (HighBitSel) for +real-true16 asm
Patch1:		0003-true16-f16-cvt-llvm23.patch
# LLVM 23 true16: v_lshlrev_b16 needs .l/.h for int8 pack
Patch2:		0004-true16-lshl-b16-llvm23.patch

BuildRequires:	rocm-rpm-macros
BuildRequires:	cmake
BuildRequires:	ninja
BuildRequires:	git-core
BuildRequires:	rocm-cmake
BuildRequires:	hipcc
BuildRequires:	rocminfo
BuildRequires:	clang-tools
BuildRequires:	rocm-hip-devel
BuildRequires:	clang >= %{rocm_llvm_maj_ver}
BuildRequires:	hipblas-common-devel
BuildRequires:	hipblas-devel
BuildRequires:	rocblas-devel
BuildRequires:	origami-devel
BuildRequires:	stinkytofu-devel
BuildRequires:	python%{pyver}dist(rocisa)
BuildRequires:	python
BuildRequires:	python%{pyver}dist(pyyaml)
BuildRequires:	python%{pyver}dist(msgpack)
BuildRequires:	python%{pyver}dist(joblib)
BuildRequires:	pkgconfig(msgpack-c)
BuildRequires:	boost-devel
BuildRequires:	cmake(msgpack-cxx)
BuildRequires:	llvm-devel
BuildRequires:	stdc++-static-devel

# No gfx803 — TensileLite/extops don't support GFX8

%description
hipBLASLt provides high-performance GEMM using TensileLite device libraries.
GPU targets are RDNA3/4 (see macros.rocm %%rocm_gpu_targets_hipblaslt).
Polaris/gfx803 is not supported by upstream TensileLite.

%package devel
Summary:	Development files for hipblaslt
Group:		Development/C++
Requires:	%{name}%{?_isa} = %{version}-%{release}
Requires:	rocm-hip-devel
Requires:	hipblas-common-devel
Provides:	hipblaslt-devel = %{EVRD}

%description devel
Headers and CMake package for hipBLASLt.

%prep
%autosetup -n hipblaslt -p1

%build
# Use clang++ as host CXX (hipcc breaks CMake compile-feature detection on Clang 23)
export CXX=clang++
export CC=clang
export HIPCXX=clang
export ROCM_PATH=%{_prefix}
export HIP_PATH=%{_prefix}
export HIP_DEVICE_LIB_PATH=%{_libdir}/amdgcn/bitcode
CXXFLAGS=$(printf '%s' "%{optflags}" | sed -E 's/-mfpmath=[^ ]+//g; s/ -m[a-z0-9+.=]+//g')
export CXXFLAGS
export CFLAGS="$CXXFLAGS"
export LDFLAGS=$(printf '%s' "%{?__global_ldflags}" | sed -E 's/-mfpmath=[^ ]+//g; s/ -m[a-z0-9+.=]+//g')
export CMAKE_HIP_FLAGS="%{rocm_hip_clang_flags}"
export HIPBLASLT_BUILD_JOBS=8
export TENSILELITE_BUILD_PARALLEL_LEVEL=8

# Keep ROCm path flags out of CMAKE_CXX_FLAGS (host-only objects reject unused --rocm-*).
%cmake %{rocm_cmake_fhs} \
	-DCMAKE_BUILD_TYPE=Release \
	-DCMAKE_CXX_COMPILER=clang++ \
	-DCMAKE_CXX_FLAGS="$CXXFLAGS" \
	-DCMAKE_HIP_FLAGS="%{rocm_hip_clang_flags}" \
	-DGPU_TARGETS="%{rocm_gpu_targets_hipblaslt}" \
	-DHIPBLASLT_ENABLE_CLIENT=OFF \
	-DHIPBLASLT_BUILD_TESTING=OFF \
	-DHIPBLASLT_ENABLE_SAMPLES=OFF \
	-DHIPBLASLT_ENABLE_ROCROLLER=OFF \
	-DHIPBLASLT_ENABLE_BLIS=OFF \
	-DHIPBLASLT_ENABLE_MARKER=OFF \
	-DHIPBLASLT_ENABLE_FETCH=OFF \
	-DHIPBLASLT_BUNDLE_PYTHON_DEPS=OFF \
	-DTENSILELITE_BUILD_PARALLEL_LEVEL=8 \
	-DHIPBLASLT_ENABLE_HOST=ON \
	-DHIPBLASLT_ENABLE_DEVICE=ON \
	-DHIPBLASLT_ENABLE_EXTOPS=OFF \
	-DHIPBLASLT_ENABLE_MATRIX_TRANSFORM=OFF \
	-DHIPBLASLT_BUILD_SHARED_LIBS=ON \
	-DROCM_PATH=%{_prefix} \
	-DCMAKE_PREFIX_PATH=%{_prefix} \
	-G Ninja
# cmake macro leaves the shell in the build/ subdirectory
%ninja_build

%install
cd build
DESTDIR=%{buildroot} /usr/bin/ninja install -j%{?_smp_build_ncpus}%{!?_smp_build_ncpus:8}
cd ..
# Relocate cmake package if installed under non-multilib libdir
_cmakedir=$(find %{buildroot}%{_prefix} -type d -path '*/cmake/hipblaslt' 2>/dev/null | head -1)
if [ -n "$_cmakedir" ] && [ "$_cmakedir" != "%{buildroot}%{_libdir}/cmake/hipblaslt" ]; then
	mkdir -p %{buildroot}%{_libdir}/cmake
	mv "$_cmakedir" %{buildroot}%{_libdir}/cmake/
fi

%files
%license LICENSE.md
%doc README.md
%exclude %{_docdir}/hipblaslt/LICENSE.md
%{_libdir}/libhipblaslt.so.*
%{_libdir}/hipblaslt/

%files devel
%{_includedir}/hipblaslt/
# Generated CMake headers also installed at include root
%{_includedir}/hipblaslt-export.h
%{_includedir}/hipblaslt-version.h
%{_libdir}/libhipblaslt.so
%{_libdir}/cmake/hipblaslt/
