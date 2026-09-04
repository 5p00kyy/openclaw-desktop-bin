# openclaw-desktop-bin

Unofficial Arch Linux packaging for the official OpenClaw Linux desktop companion. The package repackages the upstream prebuilt x86_64 Debian release, currently `v2026.8.2`, as `openclaw-desktop-bin`.

This is community packaging, not an official OpenClaw or Arch project. Report application bugs upstream at [openclaw/openclaw](https://github.com/openclaw/openclaw); report packaging problems here.

## Scope and coexistence

- Installs the upstream desktop executable, launcher, icons, desktop entry, and the upstream CLI installer helper.
- Targets x86_64 only and has no source compilation.
- Depends on the Arch equivalents of the runtime libraries declared by the upstream `.deb`, plus the executable's directly linked libraries and its helper script's Bash runtime.
- Coexists with the AUR `openclaw` CLI/Gateway package. This package neither provides nor conflicts with `openclaw`, and does not install its CLI, systemd units, or configuration. The CLI is an optional dependency because the companion can use an existing `openclaw` executable from `PATH`.
- Has no install-time network access beyond makepkg downloading the declared, checksum-pinned release source. It has no post-install service starts, configuration edits, or self-update hook.

The upstream application can link users to releases, but package-managed installations do not self-update. Update this package through the review process below.

## Build and validation

Run these commands from any Linux environment with Docker available:

```sh
./scripts/run-tests.sh
./scripts/docker-build.sh
./scripts/docker-install-test.sh
```

`docker-build.sh` starts a fresh `archlinux:base-devel` container, installs only validation/build tools there, builds with makepkg, runs namcap against the PKGBUILD and package, and stores ignored results under `.artifacts/`. `docker-install-test.sh` installs that package into a separate fresh Arch container and checks package ownership, the complete installed file list, desktop-file validity, ELF dependency resolution, and the known CLI package paths.

The expected namcap warnings are limited to preserving the upstream binary unstripped, its ELF interpreter being reported as an unused library, Bash being detected through an `/usr/bin/env` shebang, and runtime-loaded GStreamer/AppIndicator components not being visible in the ELF dependency table. Those dependencies are intentional. Treat any additional warning as a review item.

To regenerate metadata after any PKGBUILD change, never hand-edit `.SRCINFO`. The helper uses local `makepkg` on Arch and otherwise runs it in Docker:

```sh
./scripts/regenerate-srcinfo.sh
```

## Release updates

The updater validates the release tag, stable/non-draft status, exact upstream `.deb` filename, official download URL, GitHub's SHA-256 asset digest, and the digest of downloaded bytes. It edits only `PKGBUILD` and regenerates `.SRCINFO` with `makepkg --printsrcinfo`. It never commits, pushes, publishes, opens an issue, or touches AUR state.

For a live check of the latest stable release:

```sh
./scripts/update-release.py --check
```

For a deterministic, human-directed update:

```sh
./scripts/update-release.py 2026.8.3
# inspect the diff, then rerun the clean tests/build/install validation
```

An explicit version still requires a matching stable GitHub release and exact `.deb` asset. Missing assets, missing digests, digest mismatches, prereleases, drafts, and non-official URLs fail closed. The current `v2026.8.2` release is intentionally a no-op; upstream `v2026.8.1` did not have a Linux desktop asset, so there is no fabricated 8.1-to-8.2 package history.

The scheduled/manual GitHub Actions release check is deliberately quiet when current. It can create or update one release-review issue only after a newer valid release has passed those checks. It does not modify the repository, push to AUR, or create a package automatically. A maintainer must review the generated diff and run the validation gates before committing.

## Maintainer checklist

1. Run the updater, or run the current/no-op check.
2. Review `git diff`, including the source URL, checksum, dependency changes, and `.SRCINFO`.
3. Run `./scripts/run-tests.sh`, `./scripts/docker-build.sh`, and `./scripts/docker-install-test.sh`.
4. Inspect the namcap report and investigate every actionable warning.
5. Use a clear conventional commit, then submit through the intended human AUR workflow if desired.

Automation here is quiet plumbing, not user-facing AI or automation theatre. It prepares evidence and a reviewable change; a human owns release judgment and publication.
