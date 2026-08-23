#!/usr/bin/env bash
set -euo pipefail

patch_file=${1:?patch file is required}
expected_base=${EXPECTED_BASE_SHA:?EXPECTED_BASE_SHA is required}
max_bytes=${MAX_PATCH_BYTES:-1048576}
max_files=${MAX_CHANGED_FILES:-30}

[[ -s "$patch_file" ]] || { echo "Patch is empty" >&2; exit 1; }
[[ $(wc -c <"$patch_file") -le $max_bytes ]] || { echo "Patch exceeds ${max_bytes} bytes" >&2; exit 1; }
[[ $(git rev-parse HEAD) == "$expected_base" ]] || { echo "Checkout does not match authorized base SHA" >&2; exit 1; }

default_branch=$(gh api "repos/${GITHUB_REPOSITORY}" --jq '.default_branch')
current_base=$(gh api "repos/${GITHUB_REPOSITORY}/git/ref/heads/${default_branch}" --jq '.object.sha')
if [[ "$current_base" != "$expected_base" ]]; then
  echo "Default branch moved from ${expected_base} to ${current_base}; refusing stale patch" >&2
  exit 1
fi

mapfile -t changed_files < <(git apply --numstat "$patch_file" | cut -f3-)
[[ ${#changed_files[@]} -gt 0 ]] || { echo "Patch has no files" >&2; exit 1; }
[[ ${#changed_files[@]} -le $max_files ]] || { echo "Patch changes too many files" >&2; exit 1; }

for path in "${changed_files[@]}"; do
  if [[ ! "$path" =~ ^[A-Za-z0-9._/@+-]+$ || "$path" == /* || "$path" == ../* || "$path" == */../* ]]; then
    echo "Unsafe path in patch: $path" >&2
    exit 1
  fi
  case "$path" in
    .github/*|.codex/*|AGENTS.md|*/auth.json|auth.json)
      echo "Protected path changed: $path" >&2
      exit 1
      ;;
  esac
done

if git apply --numstat "$patch_file" | grep -q $'^-\t-\t'; then
  echo "Binary changes are not allowed" >&2
  exit 1
fi

if grep '^+' "$patch_file" | grep -Eiq '(BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{20,})'; then
  echo "Possible secret detected in patch" >&2
  exit 1
fi

git apply --check "$patch_file"
git apply --index "$patch_file"

if git diff --cached --summary | grep -q 'mode 120000'; then
  echo "Symbolic links are not allowed" >&2
  exit 1
fi
