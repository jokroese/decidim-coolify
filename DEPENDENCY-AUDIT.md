# Frontend dependency audit

For developers reviewing dependency updates. See [Contributing](CONTRIBUTING.md#preparing-a-decidim-upgrade) for the upgrade workflow.

Checked on **27 October 2026** with the pinned Node 22 image (npm 10.9.9), using `npm audit --package-lock-only --json` against a read-only copy of the cleaned manifests. This is a dated audit result, not a complete runtime-image or browser-bundle vulnerability assessment.

## Cleanup result

Removed the unused npm development packages `@decidim/dev`, `@decidim/eslint-config`, `@decidim/prettier-config` and `@decidim/stylelint-config`. Regenerating the lockfile removed all **401 development-only package entries**, reducing the package-entry count from **1,646 to 1,245**, including the root entry. No retained package changed version, and no new package paths were added. The separate Ruby `decidim-dev` gem remains because the Ruby lint configuration uses it.

## Remaining findings

The refreshed audit reports **13 findings: 1 high, 11 moderate and 1 low**. Some entries aggregate advisories from dependencies; they are not necessarily distinct vulnerabilities. The earlier audit reported 26 findings, including 5 high. Advisory feeds can change between runs.

The remaining high entry is `serialize-javascript` 6.0.2, reached through the asset-build tooling. npm reports [unsafe serialization](https://github.com/advisories/GHSA-5c6j-r48x-rmvq), [CPU exhaustion](https://github.com/advisories/GHSA-qj8w-gfj5-8c6v) and [unescaped script content](https://github.com/advisories/GHSA-m5mm-p8h7-m29v). This dependency remains needed by the current locked build toolchain; the cleanup does not resolve these advisories.

The Dockerfile installs npm packages and compiles assets in the build stage. Node and `node_modules` are excluded from the runtime stage. Builds use dummy application secrets and reviewed source. This reduces exposure but does not establish that all generated assets are free of vulnerabilities.

Review compatible upstream dependency updates separately, then rebuild assets and run the full smoke test. Avoid a blanket `npm audit fix` that changes the coordinated Decidim package versions. The remaining moderate and low findings also require review when dependencies are updated.
