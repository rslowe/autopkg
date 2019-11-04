#!/Library/AutoPkg/Python3/Python.framework/Versions/Current/bin/python3
#
# Copyright 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""See docstring for MunkiInstallsItemsCreator class"""

import plistlib
import subprocess

from autopkglib import Processor, ProcessorError, log

try:
    from Foundation import NSDictionary
except ImportError:
    log("WARNING: Failed 'from Foundation import NSDictionary' in " + __name__)

__all__ = ["MunkiInstallsItemsCreator"]


class MunkiInstallsItemsCreator(Processor):
    """Generates an installs array for a pkginfo file."""

    input_variables = {
        "installs_item_paths": {
            "required": True,
            "description": "Array of paths to create installs items for.",
        },
        "faux_root": {
            "required": False,
            "description": "The root of an expanded package or filesystem.",
        },
        "version_comparison_key": {
            "required": False,
            "description": (
                "Set 'version_comparison_key' for installs items. "
                "If this is a string, it is set to this value for "
                "all items given to 'installs_item_paths'. If this "
                "is a dictionary, takes a mapping of a path as "
                "given to 'installs_item_paths' to the desired "
                "version_comparison_key.\n"
                "Example:\n"
                "{'/Applications/Foo.app': 'CFBundleVersion',\n"
                "'/Library/Bar.plugin': 'CFBundleShortVersionString'}"
            ),
        },
    }
    output_variables = {
        "additional_pkginfo": {
            "description": "Pkginfo dictionary containing installs array."
        }
    }
    description = __doc__

    def create_installs_items(self):
        """Calls makepkginfo to create an installs array."""
        faux_root = ""
        if self.env.get("faux_root"):
            faux_root = self.env["faux_root"].rstrip("/")

        args = ["/usr/local/munki/makepkginfo"]
        for item in self.env["installs_item_paths"]:
            args.extend(["-f", faux_root + item])

        # Call makepkginfo.
        try:
            proc = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            (out, err) = proc.communicate()
        except OSError as err:
            raise ProcessorError(
                f"makepkginfo execution failed with error code {err.errno}: "
                f"{err.strerror}"
            )
        if proc.returncode != 0:
            raise ProcessorError(f"creating pkginfo failed: {err}")

        # Get pkginfo from output plist.
        pkginfo = plistlib.loads(out)
        installs_array = pkginfo.get("installs", [])

        if faux_root:
            for item in installs_array:
                if item["path"].startswith(faux_root):
                    item["path"] = item["path"][len(faux_root) :]
                self.output(f"Created installs item for {item['path']}")

        if "version_comparison_key" in self.env:
            for item in installs_array:
                cmp_key = None
                # If it's a string, set it for all installs items
                if isinstance(self.env["version_comparison_key"], str):
                    cmp_key = self.env["version_comparison_key"]
                # It it's a dict, find if there's a key that matches a path
                elif isinstance(self.env["version_comparison_key"], NSDictionary):
                    for path, key in list(self.env["version_comparison_key"].items()):
                        if path == item["path"]:
                            cmp_key = key

                if cmp_key:
                    # Check that we really have this key available to compare
                    if cmp_key in item:
                        item["version_comparison_key"] = cmp_key
                    else:
                        raise ProcessorError(
                            f"version_comparison_key '{cmp_key}' could not be found in "
                            f"the installs item for path '{item['path']}'"
                        )

        if "additional_pkginfo" not in self.env:
            self.env["additional_pkginfo"] = {}
        self.env["additional_pkginfo"]["installs"] = installs_array

    def main(self):
        self.create_installs_items()


if __name__ == "__main__":
    PROCESSOR = MunkiInstallsItemsCreator()
    PROCESSOR.execute_shell()
