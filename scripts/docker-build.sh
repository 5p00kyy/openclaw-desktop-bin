#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
artifact_dir="$repo_dir/.artifacts"
mkdir -p "$artifact_dir"
rm -f "$artifact_dir"/*

image=${ARCH_IMAGE:-archlinux:base-devel}
docker pull "$image" >/dev/null

docker run --rm \
  --volume "$repo_dir:/src:ro" \
  --volume "$artifact_dir:/out" \
  --env ARCH_IMAGE="$image" \
  "$image" \
  bash -ceu '
    pacman -Syu --noconfirm --needed base-devel namcap desktop-file-utils binutils python
    pacman -S --noconfirm --needed gst-libav gst-plugins-bad gst-plugins-good gtk3 libayatana-appindicator webkit2gtk-4.1
    rm -rf /build
    mkdir -p /build
    cp -a /src/. /build/
    useradd --create-home builder
    chown -R builder:builder /build
    # Install dependencies as container root, then keep makepkg unprivileged.
    su builder -s /bin/bash -c "cd /build && makepkg --nodeps --noconfirm --clean --cleanbuild --force"
    mapfile -t packages < <(find /build -maxdepth 1 -type f -name "*.pkg.tar.*" -print)
    test "${#packages[@]}" -eq 1
    namcap /build/PKGBUILD "${packages[0]}" | tee /out/namcap.txt
    cp "${packages[0]}" /out/
    sha256sum "${packages[0]}" | tee /out/package.sha256
  '

printf 'Built package(s):\n'
find "$artifact_dir" -maxdepth 1 -type f -name '*.pkg.tar.*' -printf '  %f\n'
printf 'Namcap report: %s\n' "$artifact_dir/namcap.txt"
