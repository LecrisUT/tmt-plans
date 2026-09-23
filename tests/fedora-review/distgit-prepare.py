#!/usr/bin/python3
# /// script
# dependencies = [ ]
# ///

import argparse
import logging
import os
import subprocess
from pathlib import Path

import utils

logging.basicConfig(level="INFO")
logger = logging.getLogger(Path(__file__).name)


def main(args: argparse.Namespace) -> None:
    dist_git_path = utils.get_dist_git(args.koji_task_id)
    utils.get_koji_build(args.koji_task_id)

    # Find the other files
    # TODO: The SRPM should be enough?
    spec_files = list(dist_git_path.glob("*.spec"))
    if len(spec_files) > 1:
        logger.warning("More than 1 spec file found")
    if spec_files:
        utils.save_env("SPEC_FILE", spec_files[0])
    else:
        logger.error("No spec file found?")
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--koji-task-id", default=os.environ.get("KOJI_TASK_ID"))

    args = parser.parse_args()
    try:
        main(args)
    except (subprocess.CalledProcessError, SystemExit):
        logger.error("Prepare failed!")
        raise SystemExit(1)
    except Exception as exc:
        logger.error("Unexpected prepare failure", exc_info=exc)
        raise SystemExit(2)
