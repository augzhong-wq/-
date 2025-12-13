from __future__ import annotations

import sys

from fiw.cli import build_daily, build_site, build_weekly, collect, push_weekly, serve


def main() -> None:
    # 兼容：python -m fiw <subcommand>
    # 子命令：collect | build-daily | build-weekly | build-site | serve | push-weekly
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m fiw <collect|build-daily|build-weekly|serve|push-weekly> [args]")

    cmd = sys.argv[1]
    sys.argv = [sys.argv[0], *sys.argv[2:]]

    if cmd == "collect":
        collect()
    elif cmd == "build-daily":
        build_daily()
    elif cmd == "build-weekly":
        build_weekly()
    elif cmd == "build-site":
        build_site()
    elif cmd == "serve":
        serve()
    elif cmd == "push-weekly":
        push_weekly()
    else:
        raise SystemExit(f"Unknown subcommand: {cmd}")


if __name__ == "__main__":
    main()
