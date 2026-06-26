#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
HOST_NAME="com.day1company.sheets_bridge"
EXTENSION_ORIGIN="chrome-extension://jahlkdjaokmjbipfhlhnjggcgjmpeiij/"
INSTALL_ROOT="$HOME/Library/Application Support/Day1/ChromeSheetsBridge/native-host"
INSTALL_BIN_DIR="$INSTALL_ROOT/bin"
INSTALL_SRC_DIR="$INSTALL_ROOT/src"
MANIFEST_DIR="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
MANIFEST_TARGET="$MANIFEST_DIR/$HOST_NAME.json"
HOST_TARGET="$INSTALL_BIN_DIR/sheets-bridge-native-host"

rm -rf "$INSTALL_BIN_DIR" "$INSTALL_SRC_DIR"
mkdir -p "$INSTALL_BIN_DIR" "$INSTALL_SRC_DIR"
cp "$SCRIPT_DIR/bin/sheets-bridge-native-host" "$HOST_TARGET"
cp "$SCRIPT_DIR/src/"*.py "$INSTALL_SRC_DIR/"
chmod +x "$HOST_TARGET"
xattr -cr "$INSTALL_ROOT" 2>/dev/null || true

mkdir -p "$MANIFEST_DIR"
python3 - "$MANIFEST_TARGET" "$HOST_TARGET" "$HOST_NAME" "$EXTENSION_ORIGIN" <<'PY'
from pathlib import Path
import json
import sys

target, host_path, host_name, extension_origin = sys.argv[1:]
manifest = {
    "name": host_name,
    "description": "Chrome Sheets Bridge native host for local review package persistence.",
    "path": host_path,
    "type": "stdio",
    "allowed_origins": [extension_origin],
}
Path(target).write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
PY

printf '%s\n' "$MANIFEST_TARGET"
