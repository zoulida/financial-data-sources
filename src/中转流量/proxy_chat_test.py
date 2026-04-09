import argparse

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="测试本地中转代理是否可用")
    parser.add_argument(
        "--proxy",
        default="http://127.0.0.1:9182",
        help="本地代理地址，默认使用 http://127.0.0.1:9182",
    )
    parser.add_argument(
        "--url",
        default="https://example.com",
        help="用于测试代理连通性的目标地址",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="请求超时时间（秒）",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with httpx.Client(proxy=args.proxy, timeout=args.timeout, http2=False, follow_redirects=True) as client:
        response = client.get(args.url)

    print(f"proxy      : {args.proxy}")
    print(f"target url : {response.url}")
    print(f"status     : {response.status_code}")
    print("headers    :")
    for key, value in list(response.headers.items())[:10]:
        print(f"  {key}: {value}")

    text = response.text.strip()
    preview = text[:500] if text else "<empty body>"
    print("body preview:")
    print(preview)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
