#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
temporary=$(mktemp "$repo_dir/.SRCINFO.XXXXXX")
trap 'rm -f "$temporary"' EXIT

if command -v makepkg >/dev/null 2>&1; then
  (cd "$repo_dir" && makepkg --printsrcinfo) > "$temporary"
elif command -v docker >/dev/null 2>&1; then
  image=${ARCH_IMAGE:-archlinux:base-devel}
  docker run --rm --volume "$repo_dir:/src:ro" "$image" bash -ceu '
    mkdir /build
    cp /src/PKGBUILD /build/PKGBUILD
    useradd --create-home builder
    chown -R builder:builder /build
    su builder -s /bin/bash -c "cd /build && makepkg --printsrcinfo"
  ' > "$temporary"
else
  printf 'makepkg or Docker is required to regenerate .SRCINFO\n' >&2
  exit 1
fi

mv "$temporary" "$repo_dir/.SRCINFO"
trap - EXIT
