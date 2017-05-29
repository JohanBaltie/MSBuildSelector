import glob
from itertools import product
import os

from .build_info import BuildInfo

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

    def read_configuration(self):
        """
        Retrieve all the information mandatory or optional that will be used to
        create the quick panel and launch the build.
        """

        # Set the directory to the one of the project
        project_file_name = self.window.project_file_name()
        self.directory = os.path.dirname(project_file_name)

        # retrieve the settings
        settings = load_settings("MSBuildSelector.sublime-settings")
        self.file_regex = settings.get("file_regex")

        # Retrieve the project info
        project_selector = self.window.project_data().get("msbuild_selector")

        # Is there something specified ?
        if (project_selector is None):
            error_message("MSBuildSelector: A \"msbuild_selector\" section "
                          "must be configured in the project.")
            return False

        # override command if provided
        self.msbuild_cmd = project_selector.get("command",
                                                settings.get("command"))
        if not os.path.exists(self.msbuild_cmd):
            error_string = ("MSBuildSelector: "
                            "\"{0}\" does not exists").format(self.msbuild_cmd)
            error_message(error_string)
            return False
        self.msbuild_cmd = os.path.normpath(self.msbuild_cmd)
        print(self.msbuild_cmd)

        # Retrieve all the infos
        self.builds = project_selector.get("projects", [])
        self.environment = project_selector.get("environment")

        # We should at least have one platform/configuration,
        self.platforms = project_selector.get("platforms",
                                              settings.get("platforms"))
        if ((self.platforms is None) or
                (0 == len(self.platforms))):
            error_message("MSBuildSelector: No platform configured.")
            return False

        self.configurations = \
            project_selector.get("configurations",
                                 settings.get("configurations"))
        if ((self.configurations is None) or
                (0 == len(self.configurations))):
            error_message("MSBuildSelector: No configuration configured.")
            return False

        # Patterns are mandatory
        self.patterns = project_selector.get("patterns")
        if ((self.patterns is None) or
                (0 == len(self.patterns))):
            error_message("MSBuildSelector: A \"patterns\" section must be "
                          "defined in the project.")
            return False

        # Everything ok
        return True

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
            if self.environment is not None:
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
            build_info = BuildInfo(build.get("name"),
                                   build.get("file_name"),
                                   build.get("directory"))
            self.add_build_configurations(build_info,
                                          panel_builds,
                                          build_systems)

    def start_building(self, build_systems, index):
        """
        Function called by the quick panels to start a build
        """

        # Canceled ?
        if (index == -1):
            return

        # Nope, there is something !
        cmd = build_systems[index]
        cmd["file_regex"] = self.file_regex
        self.window.run_command("show_panel",
                                {"panel": "output.exec"})
        output_panel = self.window.get_output_panel("exec")
        output_panel.settings().set("result_base_dir", cmd["working_dir"])
        print("Cmd: \"{Cmd}\"".format(Cmd=cmd))
        print("Result: {0}", self.window.run_command("exec", cmd))
