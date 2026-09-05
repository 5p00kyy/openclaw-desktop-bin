#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
artifact_dir="${root}/.artifacts"
mkdir -p "$artifact_dir"
find "$artifact_dir" -maxdepth 1 -type f \
  \( -name 'openclaw-desktop-*.pkg.tar.*' -o -name 'namcap.txt' -o -name 'package.sha256' \) \
  -delete

docker run --rm \
  -v "${root}:/input:ro" \
  -v "${root}/.artifacts:/output" \
  archlinux:base-devel \
  bash -euo pipefail -c '
    pacman -Syu --noconfirm --needed \
      at-spi2-core bash cairo dbus gdk-pixbuf2 git glib2 gst-libav \
      gst-plugins-bad gst-plugins-good gtk3 hicolor-icon-theme \
      libayatana-appindicator libsoup3 namcap nodejs pkgconf python-gobject rust \
      webkit2gtk-4.1 xorg-server-xvfb xorg-xauth
    useradd --create-home builder
    install -d -o builder -g builder /build
    cp -a /input/. /build/
    rm -rf /build/.artifacts /build/src /build/pkg
    chown -R builder:builder /build
    su builder -c "cd /build && makepkg --cleanbuild --noconfirm"
    mapfile -t packages < <(find /build -maxdepth 1 -type f \
      -name "openclaw-desktop-[0-9]*.pkg.tar.zst" ! -name "*-debug-*" -print)
    ((${#packages[@]} == 1))
    package=${packages[0]}
    namcap /build/PKGBUILD "$package" | tee /output/namcap.txt
    cp "$package" /output/
    sha256sum "$package" | tee /output/package.sha256
  '
