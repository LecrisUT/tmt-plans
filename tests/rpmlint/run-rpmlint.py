#!/usr/bin/python3
# /// script
# dependencies = [
#   "tomli-w",
# ]
# ///

import logging
import subprocess
from pathlib import Path
from typing import Any

import tomli_w

from utils import TestEnv

logging.basicConfig(level="INFO")
logger = logging.getLogger(Path(__file__).name)

CI_CONFIG_SECTION = "rpmlint"

rc_file: Path | None = None
toml_file: Path | None = None


def prepare(env: TestEnv) -> None:
    """
    - Get the rpms
    - Get config files/settings (``*.rpmlintrc`` and ``rpmint.toml``)
    """
    global rc_file, toml_file

    env.get_rpms()
    if config := env.get_config(CI_CONFIG_SECTION):
        if rc_content := config.get("rc"):
            rc_content: str
            rc_file = env.workdir / "rpmlintrc"
            rc_file.write_text(rc_content)
        if toml_content := config.get("toml"):
            toml_content: dict[str, Any]
            toml_file = env.workdir / "rpmlint.toml"
            with toml_file.open("wb") as f:
                tomli_w.dump(toml_content, f)
    else:
        rc_files = list(env.git_dir.glob("*.rpmlintrc"))
        if len(rc_files) > 1:
            logger.warning("More than 1 rpmlintrc file found")
        if rc_files:
            logger.info("Found rpmlintrc file")
            rc_file = rc_files[0]
        if (env.git_dir / "rpmlint.toml").exists():
            logger.info("Found rpmlint.toml file")
            toml_file = env.git_dir / "rpmlint.toml"


def main(env: TestEnv) -> None:
    """
    Run rpmlint
    """
    rpmlint_args = []
    if rc_file:
        rpmlint_args.extend(["-r", rc_file])
    if toml_file:
        rpmlint_args.extend(["-c", toml_file])
    rpmlint_args.append(str(env.spec_file))
    rpmlint_args.extend([str(rpm) for rpm in env.rpms])
    logger.info(f"Running rpmlint with: {rpmlint_args}")
    subprocess.run(
        ["rpmlint", *rpmlint_args],
        check=True,
    )


if __name__ == "__main__":
    env = TestEnv.from_env_variables()
    try:
        prepare(env)
        main(env)
    except SystemExit:
        raise
    except subprocess.CalledProcessError:
        logger.error("Rpmlint failed!")
        raise SystemExit(1)
    except Exception as exc:
        logger.error("Unexpected rpmlint failure", exc_info=exc)
        raise SystemExit(2)
