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
    """
    Prepare for rpmlint from a copr-build
    """
    # For now we assume a testing-farm environment (not multihost-pipeline).
    utils.save_env("RPM_FILES", "/var/share/test-artifacts/*.rpm")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--copr-project", default=os.environ.get("PACKIT_COPR_PROJECT"))
    # TODO: Migrate to tmt artifacts
    # TODO: Get the rpmlint that upstream passes somehow

    args = parser.parse_args()
    try:
        main(args)
    except (subprocess.CalledProcessError, SystemExit):
        logger.error("Prepare failed!")
        raise SystemExit(1)
    except Exception as exc:
        logger.error("Unexpected prepare failure", exc_info=exc)
        raise SystemExit(2)
