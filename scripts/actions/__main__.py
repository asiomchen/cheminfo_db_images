"""Command-line entrypoint for GitHub Actions workflow helpers."""

from __future__ import annotations

import argparse
import os

from . import docs, matrices


def add_common_image_args(parser: argparse.ArgumentParser) -> None:
    """Add registry/package arguments shared by runtime image commands."""
    parser.add_argument("--registry", default="ghcr.io")
    parser.add_argument("--image-owner", required=True)
    parser.add_argument("--image-name", required=True)
    parser.add_argument("--dist-image-name", required=True)
    parser.add_argument("--rocky-version", required=True)
    parser.add_argument("--pg-majors", required=True)


def write_outputs(outputs: matrices.ActionOutputs) -> None:
    """Write matrix command outputs to the GitHub Actions output file."""
    outputs.write(os.environ.get("GITHUB_OUTPUT"))


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for workflow helper commands."""
    parser = argparse.ArgumentParser(prog="python3 -m scripts.actions")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bingo_dist = subparsers.add_parser("prepare-bingo-dist")
    bingo_dist.add_argument("--image-name", required=True)
    bingo_dist.add_argument("--mode", required=True)
    bingo_dist.add_argument("--bingo-version", default="")
    bingo_dist.add_argument("--min-bingo-version", default="")
    bingo_dist.add_argument("--max-bingo-version", default="")
    bingo_dist.add_argument("--pg-majors", required=True)

    bingo_dist_latest = subparsers.add_parser("prepare-bingo-dist-latest")
    bingo_dist_latest.add_argument("--image-name", required=True)
    bingo_dist_latest.add_argument("--pg-majors", required=True)

    rdkit_dist = subparsers.add_parser("prepare-rdkit-dist")
    rdkit_dist.add_argument("--image-name", required=True)
    rdkit_dist.add_argument("--mode", required=True)
    rdkit_dist.add_argument("--rdkit-ref", default="")
    rdkit_dist.add_argument("--min-rdkit-version", default="")
    rdkit_dist.add_argument("--max-rdkit-version", default="")
    rdkit_dist.add_argument("--pg-majors", required=True)

    rdkit_dist_all = subparsers.add_parser("prepare-rdkit-dist-all")
    rdkit_dist_all.add_argument("--image-name", required=True)
    rdkit_dist_all.add_argument("--min-rdkit-version", required=True)
    rdkit_dist_all.add_argument("--max-rdkit-version", default="")
    rdkit_dist_all.add_argument("--pg-majors", required=True)

    for command in ("prepare-bingo-runtime", "prepare-bingo-runtime-all"):
        subparser = subparsers.add_parser(command)
        add_common_image_args(subparser)
        subparser.add_argument("--mode", default="range")
        subparser.add_argument("--bingo-version", default="")
        subparser.add_argument("--min-bingo-version", default="")
        subparser.add_argument("--max-bingo-version", default="")

    for command in ("prepare-rdkit-runtime", "prepare-rdkit-runtime-all"):
        subparser = subparsers.add_parser(command)
        add_common_image_args(subparser)
        subparser.add_argument("--mode", default="range")
        subparser.add_argument("--rdkit-version", default="")
        subparser.add_argument("--min-rdkit-version", default="")
        subparser.add_argument("--max-rdkit-version", default="")

    update_docs = subparsers.add_parser("update-docs")
    update_docs.add_argument("extension", choices=("bingo", "rdkit"))
    update_docs.add_argument("--package-name", required=True)
    return parser


def main() -> None:
    """Run a workflow helper command."""
    args = build_parser().parse_args()

    if args.command == "prepare-bingo-dist":
        write_outputs(matrices.prepare_bingo_dist(
            args.image_name,
            args.mode,
            args.bingo_version,
            args.min_bingo_version,
            args.max_bingo_version,
            args.pg_majors,
        ))
    elif args.command == "prepare-bingo-dist-latest":
        write_outputs(matrices.prepare_bingo_dist_latest(args.image_name, args.pg_majors))
    elif args.command == "prepare-rdkit-dist":
        write_outputs(matrices.prepare_rdkit_dist(
            args.image_name,
            args.mode,
            args.rdkit_ref,
            args.min_rdkit_version,
            args.max_rdkit_version,
            args.pg_majors,
        ))
    elif args.command == "prepare-rdkit-dist-all":
        write_outputs(matrices.prepare_rdkit_dist_all(
            args.image_name,
            args.min_rdkit_version,
            args.max_rdkit_version,
            args.pg_majors,
        ))
    elif args.command == "prepare-bingo-runtime":
        write_outputs(matrices.prepare_bingo_runtime(
            args.registry,
            args.image_owner,
            args.image_name,
            args.dist_image_name,
            args.rocky_version,
            args.pg_majors,
            args.mode,
            args.bingo_version,
            args.min_bingo_version,
            args.max_bingo_version,
        ))
    elif args.command == "prepare-bingo-runtime-all":
        write_outputs(matrices.prepare_bingo_runtime_all(
            args.registry,
            args.image_owner,
            args.image_name,
            args.dist_image_name,
            args.rocky_version,
            args.pg_majors,
            args.min_bingo_version,
            args.max_bingo_version,
        ))
    elif args.command == "prepare-rdkit-runtime":
        write_outputs(matrices.prepare_rdkit_runtime(
            args.registry,
            args.image_owner,
            args.image_name,
            args.dist_image_name,
            args.rocky_version,
            args.pg_majors,
            args.mode,
            args.rdkit_version,
            args.min_rdkit_version,
            args.max_rdkit_version,
        ))
    elif args.command == "prepare-rdkit-runtime-all":
        write_outputs(matrices.prepare_rdkit_runtime_all(
            args.registry,
            args.image_owner,
            args.image_name,
            args.dist_image_name,
            args.rocky_version,
            args.pg_majors,
            args.min_rdkit_version,
            args.max_rdkit_version,
        ))
    elif args.command == "update-docs":
        docs.update_docs(args.extension, args.package_name)
    else:
        raise RuntimeError(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
