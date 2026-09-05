#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
artifact_dir="$repo_dir/.artifacts"
mapfile -t packages < <(find "$artifact_dir" -maxdepth 1 -type f \
  -name 'openclaw-desktop-[0-9]*.pkg.tar.*' ! -name '*-debug-*' -print)
if ((${#packages[@]} != 1)); then
  printf 'expected one source-built package; found %d; run scripts/docker-build.sh first\n' \
    "${#packages[@]}" >&2
  exit 1
fi
package=${packages[0]}

image=${ARCH_IMAGE:-archlinux:base-devel}
docker pull "$image" >/dev/null

docker run --rm \
  --volume "$artifact_dir:/artifacts:ro" \
  "$image" \
  bash -ceu '
    pacman -Syu --noconfirm --needed base-devel desktop-file-utils binutils
    pacman -S --noconfirm --needed gst-libav gst-plugins-bad gst-plugins-good gtk3 libayatana-appindicator webkit2gtk-4.1
    mapfile -t packages < <(find /artifacts -maxdepth 1 -type f \
      -name "openclaw-desktop-[0-9]*.pkg.tar.*" ! -name "*-debug-*" -print)
    ((${#packages[@]} == 1))
    package=${packages[0]}
    pacman -U --noconfirm "$package"
    pacman -Qkk openclaw-desktop

    expected=(
      /usr/bin/openclaw-desktop
      /usr/lib/OpenClaw/install-cli.sh
      /usr/share/applications/OpenClaw.desktop
      /usr/share/licenses/openclaw-desktop/LICENSE
      /usr/share/icons/hicolor/32x32/apps/openclaw-desktop.png
      /usr/share/icons/hicolor/128x128/apps/openclaw-desktop.png
      /usr/share/icons/hicolor/256x256@2/apps/openclaw-desktop.png
      /usr/share/icons/hicolor/512x512/apps/openclaw-desktop.png
    )
    mapfile -t actual < <(pacman -Ql openclaw-desktop | awk "\$2 !~ /\/$/ {print \$2}" | sort)
    mapfile -t sorted_expected < <(printf "%s\\n" "${expected[@]}" | sort)
    diff -u <(printf "%s\\n" "${sorted_expected[@]}") <(printf "%s\\n" "${actual[@]}")
    for path in "${expected[@]}"; do pacman -Qo "$path"; done

    desktop-file-validate /usr/share/applications/OpenClaw.desktop
    ldd /usr/bin/openclaw-desktop | tee /tmp/openclaw-desktop.ldd
    ! grep -q "not found" /tmp/openclaw-desktop.ldd

    # The CLI package owns the different /usr/bin/openclaw and Node module
    # paths. This package must not introduce those or a service/config file.
    for forbidden in \
      /usr/bin/openclaw \
      /usr/lib/node_modules/openclaw \
      /usr/lib/systemd/system/openclaw.service \
      /etc/openclaw; do
      test ! -e "$forbidden"
    done
    ! pacman -Ql openclaw-desktop | grep -E "(^|/)(systemd|openclaw\.conf)(/|$)"
  '
