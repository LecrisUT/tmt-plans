#!/usr/bin/python3

import logging
import os
import subprocess
import shutil
from pathlib import Path
from enum import Enum
import json
import yaml
from typing import Any

from utils import TestEnv

logging.basicConfig(level="INFO")
logger = logging.getLogger(Path(__file__).name)

# Expose these to the users
FEDORA_REVIEW_RESULTS = [
    "fedora-review.log.gz",
    "files.dir",
    "licensecheck.txt",
    "review.json",
    "review.txt",
    "rpmlint.txt",
]


class Result(Enum):
    INFO = "info"
    FAIL = "fail"
    PASS = "pass"


def dump_results_yaml(issues: int):
    """
    https://tmt.readthedocs.io/en/stable/spec/results.html
    """
    result = Result.FAIL if issues else Result.PASS
    data = [
        {
            "name": "/",
            "result": result.value,
            "note": [f"{issues} issues"],
            "log": ["viewer.html"] + FEDORA_REVIEW_RESULTS,
        }
    ]
    path = os.path.join(os.environ.get("TMT_TEST_DATA"), "results.yaml")
    logger.info(f"Creating: {path}")
    with open(path, "w+") as fp:
        yaml.dump(data, fp)


def copy_fedora_review_results(test_env: TestEnv) -> None:
    """
    Copy fedora-review logs and results to the result directory
    """
    package_name = Path(test_env.spec_file).stem
    fedora_review_resultdir = test_env.workdir / f"review-{package_name}"
    test_resultdir = Path(os.environ["TMT_TEST_DATA"])
    logger.info(os.listdir(fedora_review_resultdir))
    for name in FEDORA_REVIEW_RESULTS:
        src = fedora_review_resultdir / name
        dst = test_resultdir / name
        logger.info(src)
        if src.exists():
            logger.info(f"Copying {name} to the test results")
            shutil.copy(src, dst)


def copy_viewer_html():
    """
    Copy viewer.html from plan data to the result directory
    """
    viewer = "viewer.html"
    logger.info(f"Copying {viewer} to the test results")
    shutil.copy(viewer, Path(os.environ["TMT_TEST_DATA"]) / viewer)


def copy_data_into_data():
    """
    There is a weird bug that we discovered with @LecrisUT. For some reason,
    when a plan has `result: custom`, the `viewer.html` stops rendering in
    Testing Farm. It is because for some reason, Oculus starts looking for it
    in `data/data/viewer.html` instead of just `data/viewer.html`.
    This is IMHO a bug but either way, until it gets resolved, we can copy the
    data there as well.
    See https://gitlab.com/testing-farm/general/-/work_items/111
    """
    shutil.copytree(
        Path(os.environ["TMT_TEST_DATA"]),
        Path(os.environ["TMT_TEST_DATA"]) / "data",
    )


def rpm_disttag(path: Path) -> str | None:
    """
    Find out the disttag value for a RPM or SRPM package.
    """
    nvr = path.name.rsplit(".", 2)[0]
    release = nvr.rsplit("-", 2)[-1]
    return release.rsplit(".", 1)[-1]


def fedora_review(test_env: TestEnv) -> dict[str, Any]:
    """
    Run fedora-review
    """
    env = os.environ.copy()
    env["REVIEW_NO_MOCKGROUP_CHECK"] = "true"

    name = Path(test_env.spec_file).stem
    cmd = ["fedora-review", "--prebuilt", "-n", name]

    # There is a weird disttag parsing bug in the `fedora-review` tool. When
    # the results contain RPM packages with different release numbers, e.g.
    # `nss-3.127.0-1.fc44.x86_64.rpm` and `nspr-4.39.0-4.fc44.x86_64.rpm``,
    # it fails to parse the dist tag even though it is the same fc44 for both.
    # https://forge.fedoraproject.org/packaging/FedoraReview/src/commit/7aeb863ec28c48d22280f9d60312c2e990a04512/src/FedoraReview/mock.py#L62-L71
    disttag = rpm_disttag(test_env.srpm)
    cmd.extend(["--define", f"DISTTAG={disttag}"])

    logger.info(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=test_env.workdir, env=env, check=True)

    path = os.path.join(test_env.workdir, "review-" + name, "review.json")
    if not os.path.exists(path):
        logger.error(f"Result JSON doesn't exist: {path}")
        raise SystemExit(1)
    logger.info("Result: {0}".format(path))

    with open(path, "r") as fp:
        review = json.load(fp)
    return review


def count_issues(review):
    issues = review.get("issues", [])
    return len(issues)


def main(test_env: TestEnv) -> None:
    """
    Run fedora-review plan
    """
    if not test_env.spec_file:
        logger.error("No spec file found!")
        raise SystemExit(1)
    if not test_env.rpms:
        logger.error("No RPM files provided")
        raise SystemExit(1)

    # At this point, the RPM packages are already downloaded in `args.workdir`,
    # we just need to copy the .spec next to them
    workdir = test_env.workdir
    shutil.copy(test_env.spec_file, workdir)

    review = fedora_review(test_env)
    issues = count_issues(review)
    dump_results_yaml(issues)
    copy_fedora_review_results(test_env)
    copy_viewer_html()
    copy_data_into_data()

    logger.error(f"Found {issues} issues")
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    env = TestEnv.from_env_variables()

    try:
        main(env)
    except SystemExit:
        raise
    except subprocess.CalledProcessError:
        logger.error("Fedora-review failed!")
        raise SystemExit(1)
    except Exception as exc:
        logger.error("Unexpected failure", exc_info=exc)
        raise SystemExit(2)
