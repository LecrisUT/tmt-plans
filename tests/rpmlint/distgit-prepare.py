#!/usr/bin/python3
# /// script
# dependencies = [
#   "ruamel.yaml",
#   "tomli-w",
# ]
# ///

import argparse
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import tomli_w

import utils

logging.basicConfig(level="INFO")
logger = logging.getLogger(Path(__file__).name)

CI_CONFIG_SECTION = "rpmlint"

RPMLINT_TOML_FILES = [
    "./fedora-ci.toml",
]


def export_rpmlint_tomls(custom_file: Path, workdir: Path, env_file: Path) -> None:
    rpmlint_data_dir = workdir / "rpmlint"
    rpmlint_data_dir.mkdir(exist_ok=True)
    for toml_file in RPMLINT_TOML_FILES:
        shutil.copy(toml_file, rpmlint_data_dir)
    if custom_file.exists():
        logger.info("Found custom rpmlint.toml file")
        shutil.copy(custom_file, rpmlint_data_dir)
    with env_file.open("a") as f:
        f.write(f"RPMLINT_TOML_FILE={rpmlint_data_dir}\n")


def set_config_files(config: dict[str, Any], args: argparse.Namespace) -> None:
    if rc_content := config.get("rc"):
        rc_content: str
        rc_file: Path = args.workdir / "rpmlintrc"
        rc_file.write_text(rc_content)
        with args.env_file.open("a") as f:
            f.write(f"RPMLINT_RC_FILE={rc_file}\n")
    distgit_toml_file: Path = args.workdir / "rpmlint.toml"
    if toml_content := config.get("toml"):
        toml_content: dict[str, Any]
        with distgit_toml_file.open("wb") as f:
            tomli_w.dump(toml_content, f)
    export_rpmlint_tomls(distgit_toml_file, args.workdir, args.env_file)


def get_config_fallback(dist_git_path: Path, args: argparse.Namespace) -> None:
    rc_files = list(dist_git_path.glob("*.rpmlintrc"))
    if len(rc_files) > 1:
        logger.warning("More than 1 rpmlintrc file found")
    if rc_files:
        logger.info("Found rpmlintrc file")
        with args.env_file.open("a") as f:
            f.write(f"RPMLINT_RC_FILE={rc_files[0]}\n")
    toml_file = dist_git_path / "rpmlint.toml"
    export_rpmlint_tomls(toml_file, args.workdir, args.env_file)


def main(args: argparse.Namespace) -> None:
    """
    Prepare for rpmlint from a dist-git
    """
    dist_git_path = utils.get_dist_git(args.koji_task_id, args.workdir)

    if config := utils.get_config(dist_git_path, CI_CONFIG_SECTION):
        set_config_files(config, args)
    else:
        get_config_fallback(dist_git_path, args)

    utils.get_koji_build(args.koji_task_id, args.workdir, args.env_file)

    # Find the other files
    # TODO: The SRPM should be enough?
    spec_files = list(dist_git_path.glob("*.spec"))
    if len(spec_files) > 1:
        logger.warning("More than 1 spec file found")
    if spec_files:
        with args.env_file.open("a") as f:
            f.write(f"SPEC_FILE={spec_files[0]}\n")
    else:
        logger.error("No spec file found?")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--koji-task-id", default=os.environ.get("KOJI_TASK_ID"))
    parser.add_argument(
        "--workdir",
        type=Path,
        default=os.environ.get("TMT_PLAN_DATA", "."),
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=os.environ.get("TMT_PLAN_ENVIRONMENT_FILE", ".env"),
    )

    args = parser.parse_args()
    try:
        main(args)
    except (subprocess.CalledProcessError, SystemExit):
        logger.error("Prepare failed!")
        raise SystemExit(1)
    except Exception as exc:
        logger.error("Unexpected prepare failure", exc_info=exc)
        raise SystemExit(2)
