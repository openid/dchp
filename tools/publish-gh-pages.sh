#!/bin/bash
# Publish content to the gh-pages branch (the GitHub Pages source). Shared by
# the publish-to-pages and deploy-preview jobs in .github/workflows/build.yml
# and by .github/workflows/preview-cleanup.yml.
#
#   publish-gh-pages.sh root <source-dir> <commit-message>
#       Replace the site root with <source-dir>'s contents, keeping the
#       PREVIEW-DO-NOT-USE/ PR previews.
#   publish-gh-pages.sh subdir <subdir> <source-dir> <commit-message>
#       Replace <subdir> with <source-dir>'s contents.
#   publish-gh-pages.sh delete <subdir> <commit-message>
#       Remove <subdir>; a no-op if it (or the branch) doesn't exist.
#
# Switches the current checkout to gh-pages, so the workflows run a copy from
# outside the work tree ($RUNNER_TEMP) rather than the checked-out file.

set -euo pipefail

mode=$1

git config user.name "OIDF GitHub Automation"
git config user.email "github@oidf.org"

# The fetch doubles as the does-the-branch-exist probe. --depth=1 because the
# branch accumulates a full site snapshot per publish and nothing here needs
# its history. The explicit refspec creates the local branch directly:
# actions/checkout configures origin to fetch only the triggering ref, so a
# bare `git fetch origin gh-pages` wouldn't give `git checkout` anything to
# resolve `gh-pages` against.
if git fetch --depth=1 origin gh-pages:gh-pages; then
  git checkout gh-pages
elif [ "$mode" = delete ]; then
  echo "No gh-pages branch; nothing to clean up."
  exit 0
else
  # Very first publish: start the branch empty.
  git checkout --orphan gh-pages
  git rm -rf --quiet .
fi

case $mode in
  root)
    src=$2 msg=$3
    find . -mindepth 1 -maxdepth 1 \
      ! -name .git ! -name PREVIEW-DO-NOT-USE -exec rm -rf {} +
    cp "$src"/* .
    ;;
  subdir)
    dir=$2 src=$3 msg=$4
    rm -rf "$dir"
    mkdir -p "$dir"
    cp "$src"/* "$dir/"
    ;;
  delete)
    dir=$2 msg=$3
    if [ ! -d "$dir" ]; then
      echo "No $dir; nothing to clean up."
      exit 0
    fi
    rm -rf "$dir"
    ;;
  *)
    echo "usage: $0 root <source-dir> <msg> | subdir <dir> <source-dir> <msg> | delete <dir> <msg>" >&2
    exit 2
    ;;
esac

# Serve files as-is (skip Pages' default Jekyll processing).
touch .nojekyll

git add -A
if git diff --cached --quiet; then
  echo "gh-pages unchanged; nothing to push."
  exit 0
fi
git commit -m "$msg"
# Retry around pushes racing another job's gh-pages push (main publish vs. PR
# previews run in different concurrency groups); concurrent commits touch
# disjoint paths, so the rebase is conflict-free.
for _ in 1 2 3; do
  git push origin gh-pages && exit 0
  git pull --rebase origin gh-pages
done
exit 1
