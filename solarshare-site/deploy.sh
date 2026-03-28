#!/bin/bash
# SolarShare EV Cebu — one-command deploy to GitHub Pages
#
# Usage:
#   ./deploy.sh <APPS_SCRIPT_URL>
#
# Example:
#   ./deploy.sh https://script.google.com/macros/s/AKfycb.../exec

set -e

APPS_SCRIPT_URL="$1"

if [ -z "$APPS_SCRIPT_URL" ]; then
  echo ""
  echo "Usage: ./deploy.sh <APPS_SCRIPT_URL>"
  echo ""
  echo "Get the URL from Google Apps Script:"
  echo "  1. Go to script.google.com"
  echo "  2. Paste Code.gs, click Deploy → New deployment"
  echo "  3. Type: Web app | Execute as: Me | Access: Anyone"
  echo "  4. Copy the Web App URL and pass it here"
  echo ""
  exit 1
fi

echo "==> Injecting Apps Script URL..."
sed -i '' "s|SOLARSHARE_API_URL|$APPS_SCRIPT_URL|g" index.html

echo "==> Checking for GitHub CLI..."
if ! command -v gh &> /dev/null; then
  echo "    Installing gh via Homebrew..."
  brew install gh
fi

echo "==> Checking GitHub auth..."
gh auth status 2>/dev/null || gh auth login

echo "==> Creating GitHub repo (solarshare-ev-cebu)..."
gh repo create solarshare-ev-cebu \
  --public \
  --description "SolarShare EV Cebu — community solar energy + EV charging map" \
  2>/dev/null && echo "    Repo created." || echo "    Repo already exists, continuing."

GITHUB_USER=$(gh api user -q .login)
REMOTE="https://github.com/${GITHUB_USER}/solarshare-ev-cebu.git"

echo "==> Setting up git..."
git init
git add index.html Code.gs
git commit -m "SolarShare EV Cebu — initial release"
git branch -M main
git remote add origin "$REMOTE" 2>/dev/null || git remote set-url origin "$REMOTE"

echo "==> Pushing to GitHub..."
git push -u origin main --force

echo "==> Enabling GitHub Pages..."
gh api "repos/${GITHUB_USER}/solarshare-ev-cebu/pages" \
  --method POST \
  -f 'source[branch]=main' \
  -f 'source[path]=/' \
  2>/dev/null || true

echo ""
echo "Done! Your site will be live in ~1 minute at:"
echo "  https://${GITHUB_USER}.github.io/solarshare-ev-cebu"
echo ""
echo "Note: It may take a minute for GitHub Pages to activate."
