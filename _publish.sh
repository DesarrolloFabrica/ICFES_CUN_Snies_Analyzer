#!/usr/bin/env bash
set -euo pipefail
export PATH="/c/Users/diego_gutierrezo/AppData/Local/gh-cli/bin:$PATH"
cd /c/Users/diego_gutierrezo/repos/ICFES_CUN_Snies_Analyzer

git add -A

if git diff --cached --name-only | grep -E '(^|/)\.env$'; then
  echo "ERROR: .env would be committed"
  exit 1
fi

git commit -m "Initial commit: Snies Analyzer CUN with HITL 50/50 documentation."

echo "COMMIT_OK"
git log -1 --oneline
git status -sb

# Create GitHub repo under authenticated user and push
REPO_NAME="ICFES_CUN_Snies_Analyzer"
gh repo create "$REPO_NAME" --private --source=. --remote=origin --push --description "Agente local ICFES CUN (Snies Analyzer) - HITL 50/50 - documentacion completa"

echo "REPO_URL:"
gh repo view --json url -q .url
