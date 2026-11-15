#!/usr/bin/env bash
# Arma una copia de bible-ai-honduras lista para hacer los videos de la app:
#   1. pone apps/bible-ai/marketing/ como <copia>/marketing/
#   2. aplica app.patch: el gancho window.__QA_VIDEO__ del harness de QA y que
#      el tsconfig de la app ignore marketing/.
# El repo de la app no cambia: esto pasa solo en la copia del runner.
#
#   bash apps/bible-ai/preparar.sh ruta/a/la/copia
#
# Si la app cambió esos archivos y el parche ya no entra, falla con un mensaje
# claro (lo ve el CI de cada PR y el chequeo de los sábados).
set -euo pipefail
aqui="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
app="${1:?uso: preparar.sh ruta/a/la/copia/de/bible-ai-honduras}"
app="$(cd "$app" && pwd)"

test -f "$app/qa-harness/mocks/scenario.js" || { echo "::error::$app no parece una copia de bible-ai-honduras"; exit 1; }
rm -rf "$app/marketing"
cp -R "$aqui/marketing" "$app/marketing"
if ! git -C "$app" apply --check "$aqui/app.patch" 2>/dev/null; then
  echo "::error::app.patch ya no entra en bible-ai-honduras ($(git -C "$app" rev-parse --short HEAD)). Hay que actualizar apps/bible-ai/app.patch."
  git -C "$app" apply --check "$aqui/app.patch" || true
  exit 1
fi
git -C "$app" apply "$aqui/app.patch"
echo "Listo: $app con marketing/ y el parche del harness ($(git -C "$app" rev-parse --short HEAD))"
