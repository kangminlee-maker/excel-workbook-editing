from __future__ import annotations

import base64
import json
import os
import socket
import struct
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

from .sheets_api import parse_spreadsheet_url


DEFAULT_CHROME_DEBUG_URL = "http://127.0.0.1:9222"


class ChromeResolverError(RuntimeError):
    """Raised when a current Google Sheets tab cannot be resolved."""


def resolve_current_sheet(
    *,
    chrome_debug_url: str = DEFAULT_CHROME_DEBUG_URL,
    tab_url_contains: str = "docs.google.com/spreadsheets",
    transport=None,
    websocket_factory=None,
) -> dict[str, str]:
    tab = _select_sheet_tab(
        _list_tabs(chrome_debug_url, transport=transport),
        tab_url_contains=tab_url_contains,
    )
    context = parse_spreadsheet_url(str(tab.get("url", "")))
    result = {
        "spreadsheet_id": context["spreadsheet_id"],
        "gid": context["gid"],
        "range": context["range"],
        "url": str(tab.get("url", "")),
        "title": str(tab.get("title", "")),
    }
    websocket_url = str(tab.get("webSocketDebuggerUrl", ""))
    if websocket_url:
        dom_context = _read_sheet_context_from_cdp(
            websocket_url=websocket_url,
            websocket_factory=websocket_factory,
        )
        if dom_context:
            parsed = parse_spreadsheet_url(dom_context.get("url", ""))
            result.update(
                {
                    "spreadsheet_id": parsed["spreadsheet_id"] or result["spreadsheet_id"],
                    "gid": parsed["gid"] or result["gid"],
                    "range": dom_context.get("range", "") or parsed["range"] or result["range"],
                    "url": dom_context.get("url", "") or result["url"],
                    "title": dom_context.get("title", "") or result["title"],
                }
            )
    if not result["spreadsheet_id"]:
        raise ChromeResolverError("Current Chrome tab is not a Google Sheet")
    return result


def _list_tabs(chrome_debug_url: str, *, transport=None) -> list[dict[str, Any]]:
    url = f"{chrome_debug_url.rstrip('/')}/json/list"
    if transport:
        tabs = transport(url)
    else:
        with urlopen(url, timeout=5) as response:
            tabs = json.loads(response.read().decode("utf-8"))
    if not isinstance(tabs, list):
        raise ChromeResolverError("Chrome debug endpoint did not return a tab list")
    return [tab for tab in tabs if isinstance(tab, dict)]


def _select_sheet_tab(tabs: list[dict[str, Any]], *, tab_url_contains: str) -> dict[str, Any]:
    for tab in tabs:
        if tab_url_contains in str(tab.get("url", "")):
            return tab
    raise ChromeResolverError("No Google Sheets tab found. Start Chrome with remote debugging or pass a spreadsheet URL.")


def _read_sheet_context_from_cdp(
    *,
    websocket_url: str,
    websocket_factory=None,
) -> dict[str, str]:
    expression = """
JSON.stringify({
  url: window.location.href,
  title: document.title,
  range: String(document.querySelector('#t-name-box')?.value || '').replaceAll('$', '').toUpperCase()
})
""".strip()
    client = websocket_factory(websocket_url) if websocket_factory else _WebSocketClient(websocket_url)
    try:
        response = client.call(
            {
                "id": 1,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": expression,
                    "returnByValue": True,
                },
            }
        )
    finally:
        client.close()
    value = (
        response.get("result", {})
        .get("result", {})
        .get("value", "")
    )
    if not value:
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        return {}
    return {key: str(parsed.get(key, "")) for key in ("url", "title", "range")}


class _WebSocketClient:
    def __init__(self, websocket_url: str) -> None:
        parsed = urlparse(websocket_url)
        if parsed.scheme != "ws":
            raise ChromeResolverError("Only ws:// Chrome debug URLs are supported")
        self.sock = socket.create_connection((parsed.hostname or "127.0.0.1", parsed.port or 80), timeout=5)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {parsed.netloc}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = self.sock.recv(4096)
        if b" 101 " not in response.split(b"\r\n", 1)[0]:
            raise ChromeResolverError("Chrome debug WebSocket handshake failed")

    def call(self, message: dict[str, Any]) -> dict[str, Any]:
        self._send(json.dumps(message, separators=(",", ":")).encode("utf-8"))
        while True:
            payload = self._recv()
            response = json.loads(payload.decode("utf-8"))
            if response.get("id") == message.get("id"):
                return response

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def _send(self, payload: bytes) -> None:
        mask = os.urandom(4)
        header = bytearray([0x81])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.extend([0x80 | 126])
            header.extend(struct.pack("!H", length))
        else:
            header.extend([0x80 | 127])
            header.extend(struct.pack("!Q", length))
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.sock.sendall(bytes(header) + mask + masked)

    def _recv(self) -> bytes:
        first = self.sock.recv(2)
        if len(first) < 2:
            raise ChromeResolverError("Chrome debug WebSocket closed")
        opcode = first[0] & 0x0F
        length = first[1] & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._recv_exact(8))[0]
        masked = bool(first[1] & 0x80)
        mask = self._recv_exact(4) if masked else b""
        payload = self._recv_exact(length)
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        if opcode == 0x8:
            raise ChromeResolverError("Chrome debug WebSocket closed")
        return payload

    def _recv_exact(self, size: int) -> bytes:
        chunks = []
        remaining = size
        while remaining:
            chunk = self.sock.recv(remaining)
            if not chunk:
                raise ChromeResolverError("Chrome debug WebSocket closed")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
