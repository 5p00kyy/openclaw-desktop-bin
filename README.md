# openclaw-desktop

Unofficial Arch Linux source package for the official OpenClaw Linux desktop companion.

This package builds the companion from the upstream release tag instead of repackaging a prebuilt Debian artifact. It is community packaging, not an official OpenClaw or Arch project. Report application bugs upstream at [openclaw/openclaw](https://github.com/openclaw/openclaw); report packaging problems here.

## Why this is source-built

The first official Linux binary, `v2026.8.2`, contains [upstream bug #135565](https://github.com/openclaw/openclaw/issues/135565): a fresh installation without a CLI can hide the manual remote-Gateway setup and show only the local CLI installer. Upstream merged [fix #135650](https://github.com/openclaw/openclaw/pull/135650) before `v2026.9.1`, but did not publish a Linux `.deb` or AppImage for that release.

This package builds the fixed tagged source, runs the upstream Rust test suite, and runs a package-specific native first-run regression test derived from upstream's AT-SPI harness. The native test verifies that a clean environment with no OpenClaw CLI can choose **On another computer**, see both URL and SSH transports, and reach the remote validation flow without invoking the installer.

## Package boundaries

The desktop companion and the OpenClaw CLI/Gateway are separate packages, but they are intentionally integrated upstream.

- Remote mode does not require a local CLI or local Gateway.
- Local mode requires a CLI. The application can use an existing `openclaw` executable or install a managed Node runtime and CLI under `~/.openclaw` after explicit user interaction.
- Pacman installation does not run the bundled installer, start services, edit user configuration, or contact the network beyond makepkg fetching declared source and locked build dependencies.
- The package conflicts with and replaces `openclaw-desktop-bin`, but neither provides nor conflicts with the separate `openclaw` CLI package.

## Remote Gateways

Choose **On another computer** on first launch. Connect using one of:

1. A private HTTPS endpoint such as Tailscale Serve.
2. The built-in SSH tunnel transport, with `openssh` installed and key authentication configured.
3. Bonjour/mDNS discovery from a directly reachable Gateway. Bonjour advertising is opt-in on Linux Gateway hosts.

A nearby-Gateway list is not a general network scan. A loopback-only Gateway with no Bonjour advertisement will not appear there, but the manual URL and SSH forms remain available in this fixed build.

## Build and validation

Run the clean Arch build, including the native no-CLI remote first-run test:

```sh
./scripts/docker-build.sh
```

The build fetches Cargo dependencies according to upstream's locked manifest during `prepare()`, then compiles with Cargo offline and frozen. Artifacts and `namcap` output are written under ignored `.artifacts/`.

Current `namcap` output contains only reviewed warnings: Bash is explicitly declared for the bundled helper despite contradictory shebang detection; the ELF interpreter warning is a loader-path false positive; GStreamer codecs are runtime-loaded by WebKitGTK; and Ayatana AppIndicator is runtime-loaded by the tray integration.

The release checker is advisory. It detects a newer stable source tag and creates a review issue, but deliberately does not alter `PKGBUILD` or trust a remote tag as a package checksum. A maintainer must download the candidate source, pin its digest, review the source changes, regenerate `.SRCINFO`, and pass the complete validation gate.

Regenerate `.SRCINFO` with makepkg after every PKGBUILD change. Never edit it by hand.

## Maintenance policy

Upstream release tags are reviewed manually before updates. A daily workflow detects a newer stable tag and opens or updates one review issue, but it never edits package files or publishes to GitHub or AUR. Every update requires source review, checksum refresh, clean build, native first-run test, package installation test, `ldd`, desktop-file validation, and human approval.
