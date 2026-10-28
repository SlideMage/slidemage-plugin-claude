# SPDX-FileCopyrightText: 2026 Stefan Palan, Jürgen Fleiß
# SPDX-License-Identifier: GPL-3.0-or-later
"""Proxy and connection cancellation coverage ported from SlideMage PR #20."""
import base64
import ctypes
import errno
import socket
import ssl
import threading
import time
import urllib.parse
from types import SimpleNamespace

import pytest

from claude.api.provider import AnthropicProvider
from claude.api._http import _shutdown_socket
from slidemage.plugin_api import Cancelled, ProviderError, UserMessage
from fake_http import TEST_TLS_CERT, ConnectProxy, Server, StallingServer, api_key_of, message_sse, wait_for_first_piece


def anthropic(server, **kwargs):
    p = AnthropicProvider(api_key=kwargs.pop("api_key", "sk-test"), **kwargs)
    p.base_url, p.max_retries = server.url, 0
    return p


def answer_with(server, content, stop_reason="end_turn"):
    server.body = message_sse(content, stop_reason)
    server.content_type = "text/event-stream"


def test_abort_interrupts_tcp_connect_polling(monkeypatch):
    p = AnthropicProvider(api_key="sk-test")
    p.base_url = "http://192.0.2.1"
    entered, closed = threading.Event(), threading.Event()
    outcome = []

    class Socket:
        def setblocking(self, _blocking):
            pass

        def connect_ex(self, _address):
            assert p._sock is self  # abort can reach even the first connect attempt
            entered.set()
            return errno.EINPROGRESS

        def shutdown(self, _how):
            closed.set()

        def close(self):
            closed.set()

    def select_pending(_read, _write, _exception, timeout):
        assert timeout <= 0.05
        closed.wait(timeout)
        return [], [], []

    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("192.0.2.1", 80))])
    monkeypatch.setattr(socket, "socket", lambda *_args: Socket())
    monkeypatch.setattr("claude.api._http.select.select", select_pending)
    # These are Python socket doubles; the real Winsock path is checked separately.
    monkeypatch.setattr("claude.api._http._shutdown_socket", lambda sock: sock.close() if sock else None)

    def run():
        try:
            p.chat([{"role": "user", "content": "hi"}], timeout=60)
        except ProviderError as exc:
            outcome.append(exc)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    try:
        assert entered.wait(2)
        started = time.monotonic()
        p.abort()
        worker.join(1)
        assert not worker.is_alive() and time.monotonic() - started < 1
        assert len(outcome) == 1 and isinstance(outcome[0], Cancelled)
        assert closed.is_set() and p._sock is None
    finally:
        p.abort()
        closed.set()
        worker.join(2)


def test_connect_falls_back_from_unavailable_ipv6_and_restores_the_timeout(monkeypatch):
    p = AnthropicProvider()
    calls = []

    class Socket:
        def setblocking(self, value):
            calls.append(("blocking", value))

        def connect_ex(self, target):
            assert p._sock is self
            calls.append(("connect", target))
            return errno.EINPROGRESS

        def getsockopt(self, *_args):
            return 0

        def settimeout(self, value):
            calls.append(("timeout", value))

        def close(self):
            calls.append("close")

    sock = Socket()

    def create(family, *_args):
        if family == socket.AF_INET6:
            raise OSError(errno.EAFNOSUPPORT, "IPv6 disabled")
        return sock

    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        (socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("::1", 80, 0, 0)),
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))])
    monkeypatch.setattr(socket, "socket", create)
    monkeypatch.setattr("claude.api._http.select.select", lambda _r, w, _e, _t: ([], w, []))
    assert p._create_socket(("localhost", 80), 60) is sock
    assert calls == [("blocking", False), ("connect", ("127.0.0.1", 80)), ("timeout", 60)]


def test_tcp_connect_timeout_closes_the_published_socket(monkeypatch):
    p = AnthropicProvider()
    closed = []

    class Socket:
        def setblocking(self, _value):
            pass

        def connect_ex(self, _target):
            return errno.EINPROGRESS

        def close(self):
            closed.append(True)

    clock = iter([0, 2])
    monkeypatch.setattr("claude.api._http.time.monotonic", lambda: next(clock))
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("192.0.2.1", 80))])
    monkeypatch.setattr(socket, "socket", lambda *_args: Socket())
    with pytest.raises(TimeoutError):
        p._create_socket(("192.0.2.1", 80), 1)
    assert closed == [True] and p._sock is None


def test_windows_abort_closes_the_detached_socket_handle(monkeypatch):
    calls = []

    class Socket:
        def detach(self):
            calls.append("detach")
            return 12345

        def close(self):
            calls.append("close")

    def closesocket(handle):
        calls.append(("closesocket", handle.value))

    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(ws2_32=SimpleNamespace(closesocket=closesocket)), raising=False)
    monkeypatch.setattr("claude.api._http.sys.platform", "win32")
    _shutdown_socket(Socket())
    assert calls == ["detach", ("closesocket", 12345), "close"]


# -- HTTPS proxies -----------------------------------------------------------

@pytest.fixture
def proxy_environment(monkeypatch):
    # Exercise the real environment resolver, with no developer proxy settings.
    for name in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NO_PROXY", "")
    context = ssl.create_default_context(cafile=str(TEST_TLS_CERT))
    monkeypatch.setattr(ssl, "_create_default_https_context", lambda: context)


@pytest.fixture
def https_server(proxy_environment):
    try:
        srv = Server(tls=True)
    except PermissionError:
        pytest.skip("sandbox forbids loopback sockets")
    yield srv
    srv.close()


@pytest.fixture
def proxy(https_server):
    relay = ConnectProxy(https_server.httpd.server_address)
    yield relay
    relay.close()


@pytest.mark.parametrize("variable", ["HTTPS_PROXY", "https_proxy", "ALL_PROXY"])
def test_anthropic_https_uses_connect_proxy(https_server, proxy, monkeypatch, variable):
    monkeypatch.setenv(variable, proxy.url)
    answer_with(https_server, [{"type": "text", "text": "via proxy"}])
    p = anthropic(https_server)
    # This name cannot resolve directly: only the local proxy routes it to the API.
    p.base_url = "https://api.anthropic.test"
    assert p.chat([{"role": "user", "content": "hi"}]).text == "via proxy"
    assert len(proxy.requests) == 1 and proxy.requests[0]["path"] == "api.anthropic.test:443"
    assert "proxy-authorization" not in proxy.requests[0]["headers"]
    assert https_server.requests[0]["headers"]["host"] == "api.anthropic.test"
    assert api_key_of(https_server.requests[0]) == "sk-test"


@pytest.mark.parametrize("variable", ["NO_PROXY", "no_proxy"])
def test_anthropic_no_proxy_bypasses_connect(https_server, proxy, monkeypatch, variable):
    monkeypatch.setenv("HTTPS_PROXY", proxy.url)
    monkeypatch.setenv(variable, "127.0.0.1")
    answer_with(https_server, [{"type": "text", "text": "direct"}])
    assert anthropic(https_server).chat([{"role": "user", "content": "hi"}]).text == "direct"
    assert not proxy.requests


@pytest.mark.parametrize("bypass", ["", "localhost,127.0.0.1,::1"])
@pytest.mark.parametrize("host", ["localhost", "LOCALHOST.", "127.0.0.1", "127.0.0.2", "::1"])
def test_local_requests_are_never_proxied(proxy_environment, monkeypatch, bypass, host):
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.test:8080")
    monkeypatch.setenv("NO_PROXY", bypass)
    authority = f"[{host}]" if ":" in host else host
    conn = AnthropicProvider()._connection(urllib.parse.urlsplit(f"https://{authority}:11434"), 1)
    try:
        assert conn.host == host.lower() and conn._tunnel_host is None
    finally:
        conn.close()


@pytest.mark.parametrize("variable", ["HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"])
def test_https_proxy_connection_configuration(proxy_environment, monkeypatch, variable):
    monkeypatch.setenv(variable, "http://user%40name:p%3Ass@proxy.test:8080")
    parts = urllib.parse.urlsplit("https://api.anthropic.test:8443")
    conn = AnthropicProvider()._connection(parts, 10)
    try:
        assert (conn.host, conn.port) == ("proxy.test", 8080)
        assert (conn._tunnel_host, conn._tunnel_port) == ("api.anthropic.test", 8443)
        assert conn._tunnel_headers["Proxy-Authorization"] == "Basic dXNlckBuYW1lOnA6c3M="
    finally:
        conn.close()


@pytest.mark.parametrize("variable", ["NO_PROXY", "no_proxy"])
def test_proxy_bypass_connection_configuration(proxy_environment, monkeypatch, variable):
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.test:8080")
    monkeypatch.setenv(variable, ".anthropic.test")
    conn = AnthropicProvider()._connection(urllib.parse.urlsplit("https://api.anthropic.test"), 10)
    try:
        assert conn.host == "api.anthropic.test" and conn._tunnel_host is None
    finally:
        conn.close()


def test_https_rejects_non_http_proxy_and_http_stays_direct(proxy_environment, monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "socks5://proxy.test:1080")
    p = AnthropicProvider()
    with pytest.raises(ProviderError, match="require an http:// proxy"):
        p._connection(urllib.parse.urlsplit("https://api.anthropic.test"), 10)
    conn = p._connection(urllib.parse.urlsplit("http://api.anthropic.test"), 10)
    try:
        assert conn.host == "api.anthropic.test" and conn._tunnel_host is None
    finally:
        conn.close()


def test_proxy_basic_auth_is_only_sent_to_the_proxy(https_server, proxy, monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", proxy.url.replace("http://", "http://user%40name:p%3Ass@"))
    answer_with(https_server, [{"type": "text", "text": "ok"}])
    p = anthropic(https_server)
    p.base_url = "https://api.anthropic.test:8443"
    assert p.chat([{"role": "user", "content": "hi"}]).text == "ok"
    assert proxy.requests[0]["path"] == "api.anthropic.test:8443"
    assert proxy.requests[0]["headers"]["proxy-authorization"] == "Basic " + base64.b64encode(b"user@name:p:ss").decode()
    assert "proxy-authorization" not in https_server.requests[0]["headers"]


def test_abort_ends_a_stream_through_the_connect_proxy(https_server, proxy, monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", proxy.url)
    answer_with(https_server, [{"type": "text", "text": "Hello there"}])
    body = https_server.body
    https_server.stall_after = body.index("event: content_block_delta", body.index("content_block_delta") + 1)
    p = anthropic(https_server)
    p.base_url = "https://api.anthropic.test"
    texts, outcome = [], []

    def run():
        try:
            p.stream_turn("", [], [], texts.append)
        except ProviderError as exc:
            outcome.append(exc)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    try:
        wait_for_first_piece(worker, texts)
        assert p._sock is not None and len(proxy.requests) == 1
        started = time.monotonic()
        p.abort()
        worker.join(1)
        assert not worker.is_alive() and time.monotonic() - started < 1
        assert len(outcome) == 1 and isinstance(outcome[0], Cancelled)
    finally:
        p.abort()
        https_server.delay.set()
        worker.join(2)


@pytest.mark.parametrize("stage", ["tls", "proxy_tls", "connect_tunnel"])
def test_abort_ends_stalled_connection_setup(monkeypatch, stage):
    try:
        stalled = StallingServer()
    except PermissionError:
        pytest.skip("sandbox forbids loopback sockets")
    proxy = None
    p = AnthropicProvider(api_key="sk-test")
    outcome = []
    # Isolate both uppercase and lowercase environment settings.
    for name in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NO_PROXY", "*")
    p.base_url = f"https://127.0.0.1:{stalled.address[1]}"
    worker = None
    try:
        if stage != "tls":
            monkeypatch.setenv("NO_PROXY", "")
            if stage == "proxy_tls":
                proxy = ConnectProxy(stalled.address)
                monkeypatch.setenv("HTTPS_PROXY", proxy.url)
            else:
                monkeypatch.setenv("HTTPS_PROXY", f"http://127.0.0.1:{stalled.address[1]}")
            p.base_url = "https://api.anthropic.test"

        def run():
            try:
                p.stream_turn("", [UserMessage("hi")], [], lambda _: None, timeout=60)
            except ProviderError as exc:
                outcome.append(exc)

        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        assert stalled.received.wait(3), "no ClientHello / CONNECT received"
        assert p._sock is not None
        started = time.monotonic()
        p.abort()
        worker.join(1)
        assert not worker.is_alive() and time.monotonic() - started < 1
        assert len(outcome) == 1 and isinstance(outcome[0], Cancelled)
    finally:
        p.abort()
        stalled.close()
        if proxy:
            proxy.close()
        if worker:
            worker.join(2)


def test_abort_ends_a_pending_tcp_connect(monkeypatch):
    # TEST-NET-1: never a real API. Some networks reject immediately rather than
    # leaving the SYN pending; only a pending connection can exercise this case.
    monkeypatch.setenv("NO_PROXY", "*")
    monkeypatch.setenv("no_proxy", "*")
    p = AnthropicProvider(api_key="sk-test")
    p.base_url = "https://192.0.2.1:443"
    outcome = []
    try:
        with socket.socket():
            pass
    except PermissionError:
        pytest.skip("sandbox forbids sockets")

    def run():
        try:
            p.chat([{"role": "user", "content": "hi"}], timeout=60)
        except ProviderError as exc:
            outcome.append(exc)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    try:
        deadline = time.monotonic() + 0.5
        while worker.is_alive() and time.monotonic() < deadline:
            worker.join(0.01)
        if not worker.is_alive() or p._sock is None:
            pytest.skip("network rejects the test address instead of leaving connect pending")
        # A completed TCP connection would have moved on to TLS; this test must
        # observe TCP setup itself, not another handshake timeout.
        if isinstance(p._sock, ssl.SSLSocket):
            pytest.skip("test address unexpectedly accepted TCP")
        started = time.monotonic()
        p.abort()
        worker.join(1)
        assert not worker.is_alive() and time.monotonic() - started < 1
        assert len(outcome) == 1 and isinstance(outcome[0], Cancelled)
    finally:
        p.abort()
        worker.join(2)


def test_abort_reaches_the_tls_socket_before_the_handshake(monkeypatch):
    p = AnthropicProvider(api_key="sk-test")
    entered, closed = threading.Event(), threading.Event()
    outcome = []

    class RawSocket:
        def setsockopt(self, *_args):
            pass

        def close(self):
            pass

    class TLSSocket:
        def do_handshake(self):
            assert p._sock is self
            entered.set()
            assert closed.wait(2), "abort did not close the TLS socket"
            raise OSError("handshake aborted")

        def shutdown(self, _how):
            closed.set()

        def close(self):
            closed.set()

    raw, tls = RawSocket(), TLSSocket()

    def create_socket(*_args):
        p._publish_socket(raw)
        return raw

    def wrap(_context, sock, *, server_hostname, do_handshake_on_connect):
        assert sock is raw and p._sock is raw
        assert server_hostname == "api.anthropic.com" and not do_handshake_on_connect
        return tls

    monkeypatch.setenv("NO_PROXY", "*")
    monkeypatch.setenv("no_proxy", "*")
    monkeypatch.setattr(p, "_create_socket", create_socket)
    monkeypatch.setattr(ssl.SSLContext, "wrap_socket", wrap)
    monkeypatch.setattr("claude.api._http._shutdown_socket", lambda sock: sock.close() if sock else None)

    def run():
        try:
            p.chat([{"role": "user", "content": "hi"}], timeout=60)
        except ProviderError as exc:
            outcome.append(exc)

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    try:
        assert entered.wait(2)
        p.abort()
        worker.join(1)
        assert not worker.is_alive() and len(outcome) == 1 and isinstance(outcome[0], Cancelled)
        assert p._sock is None
    finally:
        p.abort()
        closed.set()
        worker.join(2)


