#!/usr/bin/env python3
"""RTSP probe utility for camera endpoint diagnostics.

Checks:
1) TCP reachability
2) RTSP OPTIONS
3) RTSP DESCRIBE (unauthenticated)
4) RTSP DESCRIBE (Digest auth if username/password provided)
5) Optional OpenCV frame-read test
"""

import argparse
import hashlib
import re
import socket
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class RtspResponse:
    status_line: str
    raw: str


def recv_rtsp_response(sock: socket.socket, timeout: float = 4.0) -> RtspResponse:
    sock.settimeout(timeout)
    data = b""
    while True:
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\r\n\r\n" in data:
                break
        except socket.timeout:
            break
    text = data.decode(errors="replace")
    first = text.splitlines()[0] if text else "NO_RESPONSE"
    return RtspResponse(status_line=first, raw=text)


def tcp_check(host: str, port: int, timeout: float = 3.0) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        s.close()


def rtsp_options(host: str, port: int, path: str) -> RtspResponse:
    uri = f"rtsp://{host}:{port}/{path.lstrip('/')}"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(8)
    try:
        s.connect((host, port))
        req = (
            f"OPTIONS {uri} RTSP/1.0\r\n"
            f"CSeq: 1\r\n"
            f"User-Agent: homeauto-rtsp-probe\r\n\r\n"
        ).encode()
        s.sendall(req)
        return recv_rtsp_response(s)
    finally:
        s.close()


def describe_unauth(host: str, port: int, path: str) -> RtspResponse:
    uri = f"rtsp://{host}:{port}/{path.lstrip('/')}"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(8)
    try:
        s.connect((host, port))
        req = (
            f"DESCRIBE {uri} RTSP/1.0\r\n"
            f"CSeq: 2\r\n"
            f"Accept: application/sdp\r\n"
            f"User-Agent: homeauto-rtsp-probe\r\n\r\n"
        ).encode()
        s.sendall(req)
        return recv_rtsp_response(s)
    finally:
        s.close()


def _parse_digest_challenge(raw: str) -> Optional[Tuple[str, str]]:
    m = re.search(
        r'WWW-Authenticate:\s*Digest\s+realm="([^"]+)",nonce="([^"]+)"',
        raw,
        re.IGNORECASE,
    )
    if not m:
        return None
    return m.group(1), m.group(2)


def describe_digest(host: str, port: int, path: str, username: str, password: str) -> RtspResponse:
    uri = f"rtsp://{host}:{port}/{path.lstrip('/')}"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(8)
    try:
        s.connect((host, port))

        req1 = (
            f"DESCRIBE {uri} RTSP/1.0\r\n"
            f"CSeq: 10\r\n"
            f"Accept: application/sdp\r\n"
            f"User-Agent: homeauto-rtsp-probe\r\n\r\n"
        ).encode()
        s.sendall(req1)
        r1 = recv_rtsp_response(s)

        challenge = _parse_digest_challenge(r1.raw)
        if not challenge:
            return RtspResponse(status_line="NO_DIGEST_CHALLENGE", raw=r1.raw)

        realm, nonce = challenge
        ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()
        ha2 = hashlib.md5(f"DESCRIBE:{uri}".encode()).hexdigest()
        response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()

        auth = (
            "Digest "
            f'username="{username}", '
            f'realm="{realm}", '
            f'nonce="{nonce}", '
            f'uri="{uri}", '
            f'response="{response}"'
        )
        req2 = (
            f"DESCRIBE {uri} RTSP/1.0\r\n"
            f"CSeq: 11\r\n"
            f"Accept: application/sdp\r\n"
            f"Authorization: {auth}\r\n"
            f"User-Agent: homeauto-rtsp-probe\r\n\r\n"
        ).encode()
        s.sendall(req2)
        return recv_rtsp_response(s)
    finally:
        s.close()


def opencv_probe(url: str) -> Tuple[bool, bool, str]:
    try:
        import cv2
    except Exception as e:
        return False, False, f"opencv_unavailable: {e}"

    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    opened = cap.isOpened()
    ok, frame = cap.read() if opened else (False, None)
    shape = str(frame.shape) if ok and frame is not None else ""
    cap.release()
    return opened, ok, shape


def main() -> int:
    parser = argparse.ArgumentParser(description="RTSP camera endpoint probe")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=554)
    parser.add_argument("--path", default="stream1")
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument("--opencv", action="store_true", help="Attempt OpenCV frame read")
    args = parser.parse_args()

    print(f"Target: {args.host}:{args.port}/{args.path}")

    reachable = tcp_check(args.host, args.port)
    print(f"TCP reachable: {reachable}")
    if not reachable:
        return 2

    opt = rtsp_options(args.host, args.port, args.path)
    print(f"OPTIONS: {opt.status_line}")

    des = describe_unauth(args.host, args.port, args.path)
    print(f"DESCRIBE (no auth): {des.status_line}")

    if args.username and args.password:
        des_auth = describe_digest(args.host, args.port, args.path, args.username, args.password)
        print(f"DESCRIBE (digest auth): {des_auth.status_line}")

    if args.opencv:
        if args.username and args.password:
            url = f"rtsp://{args.username}:{args.password}@{args.host}:{args.port}/{args.path}"
        else:
            url = f"rtsp://{args.host}:{args.port}/{args.path}"
        opened, read_ok, shape = opencv_probe(url)
        print(f"OpenCV opened: {opened}")
        print(f"OpenCV read frame: {read_ok}")
        if shape:
            print(f"OpenCV frame shape: {shape}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
