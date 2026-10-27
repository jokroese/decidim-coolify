# Optional developer checks: install the app bundle, then run bin/ci from app/.
# Deployment validation and runtime smoke tests live in the root CI workflow.
CI.run do
  step "Style: Ruby", "bin/rubocop"
  step "Security: Gem audit", "bin/bundler-audit"
  step "Security: Brakeman code analysis", "bin/brakeman --quiet --no-pager --exit-on-warn --exit-on-error"
end
