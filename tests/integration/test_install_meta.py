#
#  Copyright (c) Honda Research Institute Europe GmbH
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are
#  met:
#
#  1. Redistributions of source code must retain the above copyright notice,
#     this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
#  3. Neither the name of the copyright holder nor the names of its
#     contributors may be used to endorse or promote products derived from
#     this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
#  IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
#  THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
#  PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
#  CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
#  EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
#  PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
#  PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
#  LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#  NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#
from __future__ import annotations

import shutil

from pathlib import Path

import pytest

from cleo.application import Application
from cleo.testers.command_tester import CommandTester
from deb_pkg_tools.package import ArchiveEntry
from deb_pkg_tools.package import inspect_package_contents

from robenv.environment.distro import DistroConfig
from robenv.environment.distro import get_distro_config
from tests.conftest import ROS_2
from tests.conftest import YieldFixture
from tests.conftest import get_ros_version


@pytest.fixture()
def _copy_meta_example_project(robenv_target_path: Path, example_project: Path) -> YieldFixture[None]:
    target_folder = robenv_target_path.parent / "src"
    target_folder.mkdir(exist_ok=True, parents=True)

    adder_meta_project = example_project / "src/adder_meta"
    adder_project = example_project / "src/adder"
    adder_srvs_project = example_project / "src/adder_srvs"

    assert adder_meta_project.exists(), "adder_meta project doesn't exist, cannot copy meta example"
    assert adder_project.exists(), "adder project doesn't exist, cannot copy meta example"
    assert adder_srvs_project.exists(), "adder_srvs project doesn't exist, cannot copy meta example"

    shutil.copytree(adder_meta_project, target_folder / adder_meta_project.name)
    shutil.copytree(adder_project, target_folder / adder_project.name)
    shutil.copytree(adder_srvs_project, target_folder / adder_srvs_project.name)

    yield

    # cleanup for space
    shutil.rmtree(target_folder, ignore_errors=True)


@pytest.fixture()
def distro_settings() -> DistroConfig:
    return get_distro_config("noetic")


@pytest.mark.skipif(get_ros_version() == ROS_2, reason="ROS2 doesn't have meta packages anymore")
@pytest.mark.usefixtures("_copy_meta_example_project")
def test_install_meta_package_should_not_contain_overwritten_files(
    init_app: Application,
    distro_settings: DistroConfig,
    dist_path: Path,
) -> None:
    # ATTENTION:
    # this test accesses the internet via `rosdep init` and `rosdep update`
    # necessary because our cached rosdep files now are mostly created on ROS2
    # variants and code the ros distro within them, this test expects correct
    # resolve to the currently used distro which mostly is `noetic`

    # adder, adder_srvs, adder_meta
    expected_built_files = 3

    dist_path.rmdir()
    assert not dist_path.exists()
    CommandTester(init_app.find("install")).execute("src")
    assert len(list(dist_path.iterdir())) == expected_built_files

    contents: dict[str, ArchiveEntry] = inspect_package_contents(
        next(filter(lambda x: "meta" in x.name, dist_path.iterdir())),
    )

    assert "/opt/ros/noetic/share/adder_meta/package.xml" in contents

    for file_to_copy in distro_settings.files_to_copy:
        assert file_to_copy not in contents
