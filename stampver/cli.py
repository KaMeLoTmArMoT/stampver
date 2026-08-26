import argparse
import json
import os
import sys

from stampver import __version__
from stampver.config import StampverConfig
from stampver.core import resolve_context
from stampver.engine import consistency_issues, stamp_workspace
from stampver.hooks import install_pre_commit_hook


def main():
    parser = argparse.ArgumentParser(
        prog="stampver",
        description="Universal date-first versioning and build stamping tool.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    stamp_parser = subparsers.add_parser(
        "stamp", help="Detect and stamp version across project files"
    )
    stamp_parser.add_argument(
        "--bump",
        choices=["patch", "minor", "major"],
        help="Bump SemVer (patch, minor, or major)",
    )
    stamp_parser.add_argument(
        "--salt",
        default="",
        help="Optional secret salt key for build hash generation",
    )
    stamp_parser.add_argument(
        "--stage",
        action="store_true",
        help="Automatically 'git add' updated files",
    )
    stamp_parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Preview files that would be updated without writing changes",
    )
    stamp_parser.add_argument(
        "--dir",
        default=".",
        help="Target project root directory (default: current directory)",
    )
    stamp_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output structured JSON payload (ideal for AI agents)",
    )

    info_parser = subparsers.add_parser(
        "info", help="Print current resolved version and build metadata"
    )
    info_parser.add_argument(
        "--dir",
        default=".",
        help="Target project root directory (default: current directory)",
    )
    info_parser.add_argument(
        "--salt",
        default="",
        help="Optional secret salt key for build hash generation",
    )
    info_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output structured JSON payload",
    )

    hook_parser = subparsers.add_parser(
        "hook-install", help="Install git pre-commit hook in target directory"
    )
    hook_parser.add_argument(
        "--dir",
        default=".",
        help="Target git project root directory (default: current directory)",
    )

    check_parser = subparsers.add_parser(
        "check",
        help="Verify base version consistency across declaration files (drift gate)",
    )
    check_parser.add_argument(
        "--dir",
        default=".",
        help="Target project root directory (default: current directory)",
    )
    check_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output structured JSON payload",
    )

    args = parser.parse_args()

    if not args.command:
        args.command = "info"
        args.dir = "."
        args.salt = ""
        args.json_output = False

    target_dir = os.path.abspath(getattr(args, "dir", "."))
    config = StampverConfig.load(target_dir)

    if args.command == "info":
        ctx = resolve_context(
            target_dir,
            format_key=config.format,
            salt=config.salt if not args.salt else args.salt,
        )
        data = {
            "full_version": ctx.full_version,
            "semver": ctx.semver,
            "date": ctx.date_str,
            "calver_code": ctx.calver_code,
            "commit_hash": ctx.commit_hash,
            "build_hash": ctx.build_hash,
        }
        if args.json_output:
            print(json.dumps(data, indent=2))
        else:
            print("=======================================")
            print(f" Full Version : {ctx.full_version}")
            print(f" SemVer Base  : {ctx.semver or '[None - CalVer Only]'}")
            print(f" UTC Date     : {ctx.date_str}")
            print(f" Git Commit   : {ctx.commit_hash}")
            print(f" Build Hash   : {ctx.build_hash}")
            print("=======================================")

    elif args.command == "check":
        issues = consistency_issues(target_dir)
        if args.json_output:
            print(json.dumps({"consistent": not issues, "issues": issues}, indent=2))
        elif issues:
            for issue in issues:
                print(f"[stampver] Version drift: {issue}", file=sys.stderr)
            print("[stampver] Version files are inconsistent.", file=sys.stderr)
            sys.exit(1)
        else:
            print("[stampver] Version files are consistent.")

    elif args.command == "stamp":
        dry_run = getattr(args, "dry_run", False)
        result = stamp_workspace(
            root_dir=target_dir,
            config=config,
            bump=args.bump,
            salt=args.salt,
            stage=args.stage,
            dry_run=dry_run,
        )

        data = {
            "status": "success" if not result.errors else "partial_success",
            "dry_run": dry_run,
            "full_version": result.context.full_version,
            "semver": result.context.semver,
            "date": result.context.date_str,
            "commit_hash": result.context.commit_hash,
            "build_hash": result.context.build_hash,
            "updated_files": result.updated_files,
            "staged_files": result.staged_files,
            "errors": result.errors,
        }

        if args.json_output:
            print(json.dumps(data, indent=2))
        else:
            prefix = "[stampver] [DRY RUN]" if dry_run else "[stampver]"
            print(f"{prefix} Stamped version: {result.context.full_version}")
            if result.updated_files:
                header = " Files that would be updated:" if dry_run else " Updated files:"
                print(header)
                for f in result.updated_files:
                    staged_msg = " (git staged)" if f in result.staged_files else ""
                    print(f"   - {f}{staged_msg}")
            else:
                print(" All version files are up to date.")
            if result.errors:
                print(" Errors encountered:")
                for err in result.errors:
                    print(f"   ! {err}", file=sys.stderr)

    elif args.command == "hook-install":
        success, message = install_pre_commit_hook(target_dir)
        if success:
            print(f"[stampver] {message}")
        else:
            print(f"[stampver] Error: {message}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
