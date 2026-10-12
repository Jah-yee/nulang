# Cutting a Release

How to publish a Nulang release with prebuilt binaries. Run
[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) first.

## 1. Bump the version

- Update `version` in `Cargo.toml` and the `VERSION` constant in
  `src/main.rs` so they match (the checklist verifies this).
- The **language version** (`[package.metadata] language-version`) only moves
  on RFC-ratified changes — usually leave it alone. See `GOVERNANCE.md` §5.
- Add a `CHANGELOG.md` entry for the new version.

## 2. Tag and push

Tags matching `v*` trigger `.github/workflows/release.yml`:

```bash
git tag v0.2.0
git push origin v0.2.0
```

## 3. Watch the workflow

The `Release` workflow first verifies that the pushed tag matches both
`Cargo.toml` and the CLI `VERSION`, then builds four targets in parallel
(`linux-x86_64`, `linux-aarch64`, `macos-aarch64`, `windows-x86_64`), runs
`cargo test --locked --release` on the native Linux build, then the `publish` job
creates a GitHub Release with:

- one `nulang-<platform>-<arch>.tar.gz` archive per supported target; the
  executable is `nulang` on Unix and `nulang.exe` on Windows
- a `.sha256` checksum per tarball
- auto-generated release notes

> Note: the `linux-aarch64` artifact is cross-compiled with the default
> feature set. The workflow installs the arm64 Python development library and
> pins PyO3's cross-Python version for that target.

## 4. Verify the release

- Open https://github.com/nulang-org/nulang/releases and confirm all 8 files
  (4 tarballs + 4 checksums) are attached.
- Smoke-test one artifact:

  ```bash
  base=https://github.com/nulang-org/nulang/releases/download/v0.2.0
  curl -fLO "$base/nulang-linux-x86_64.tar.gz"
  curl -fLO "$base/nulang-linux-x86_64.tar.gz.sha256"
  sha256sum -c nulang-linux-x86_64.tar.gz.sha256
  tar xzf nulang-linux-x86_64.tar.gz
  ./nulang-linux-x86_64 --version   # must print the version you just tagged
  ./nulang-linux-x86_64 --eval 'perform IO.print("release works")'
  ```

- Verify the executable extracted from each archive, not just a source-built
  binary. On Linux, inspect dynamic dependencies with
  `ldd ./nulang-linux-x86_64` and repeat the smoke test on a clean supported
  environment. CI builds on a runner with development libraries installed;
  that does not establish portability to another Linux distribution.
- If a release artifact is broken, stop recommending it, document the affected
  version, fix the cause, and publish a new version and tag. Do not silently
  replace binaries under an already-public tag; consumers may have pinned the
  old checksums.
