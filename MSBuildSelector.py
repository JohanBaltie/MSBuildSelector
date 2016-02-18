import glob
from itertools import product
import os

from . import BuildInfo as BuildInfo

from sublime import error_message, load_settings
from sublime_plugin import WindowCommand


class MsbuildSelector(WindowCommand):
    """
    Parent class for the selectors that will old the common thing selectors
    will need to manipulate those build infos
    """
    msbuild_parameter = \
        "/p:Platform={Platform};Configuration={Configuration}"
    file_build_label = "{Name}: {Platform}/{Configuration}"

    def initialize(self):
        """
        Retrieve all the information mandatory or optional that will be used to
        create the quick panel and launch the build.
        """

        # Set the directory to the one of the project
        project_file_name = self.window.project_file_name()
        self.directory = os.path.dirname(project_file_name)

        # retrieve the settings
        settings = load_settings("MSBuildSelector.sublime-settings")
        self.msbuild_cmd = settings.get("command")
        self.platforms = settings.get("platforms")
        self.configurations = settings.get("configurations")
        self.file_regex = settings.get("file_regex")

        # Retrieve the project info
        selector = self.window.project_data().get("msbuild_selector")

        # Is there something specified ?
        if (selector is None):
            error_message("Configure a \"msbuild_selector\" in your project.")
            return False

        # override command if provided
        overrided_command = selector.get("command")
        if overrided_command is not None:
            self.msbuild_cmd = overrided_command

        # Retrieve all the infos
        self.builds = selector.get("projects", [])
        self.patterns = selector.get("patterns")
        self.environment = selector.get("environment")

        # Patterns are mandatory
        return (self.patterns is not None)

    def list_all_projects(self):
        """
        Return the whole list of projects
        """
        for pattern in self.patterns:
            pattern_with_path = os.path.join(self.directory, pattern)
            for project in glob.iglob(pattern_with_path):
                project_path = os.path.abspath(project)
                yield project_path

    def create_build_configurations(self, build):
        """
        Create a build configuration for every pair of
        Configuration/Platform for this file and this parameters
        """

        # Main loop on all configuration/platform pairs
        for configuration, platform in product(self.configurations,
                                               self.platforms):
            parameter = \
                self.msbuild_parameter.format(Platform=platform,
                                              Configuration=configuration)
            full_name = \
                self.file_build_label.format(Name=build.name,
                                             Platform=platform,
                                             Configuration=configuration)

            # Create the "command line", handling extra parameters
            cmd = [self.msbuild_cmd, build.file_name, parameter]

            if len(build.params) > 0:
                cmd.extend(build.params)

            build_system = {
                "cmd": cmd,
                "working_dir": build.directory}
            if self.environment is None:
                build_system["env"] = self.environment

            yield (full_name, build_system)

    def add_build_configurations(self,
                                 build,
                                 panel,
                                 build_systems):
        """
        Add the various build configurations names to the panel and append them
        to the list of build systems
        """
        for full_name, build_system in self.create_build_configurations(build):
            build_systems.append(build_system)
            panel.append(full_name)

    def add_solutions_to_build(self, panel_builds, build_systems):
        """
        Add the global projects (a.k.a. solutions) to the list of possible
        builds.
        """

        for build in self.builds:
            build_info = BuildInfo.BuildInfo(build.get("name"),
                                             build.get("file_name"),
                                             build.get("directory"))
            self.add_build_configurations(build_info,
                                          panel_builds,
                                          build_systems)

    def start_building(self, build_systems, index):
        """
        Function called by the quick panels to start a build
        """
        if (index == -1):
            return

        cmd = build_systems[index]
        cmd["file_regex"] = self.file_regex
        self.window.run_command("show_panel",
                                {"panel": "output.exec"})
        output_panel = self.window.get_output_panel("exec")
        output_panel.settings().set("result_base_dir", cmd["working_dir"])
        self.window.run_command("exec", cmd)
