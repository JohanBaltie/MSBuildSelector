from sublime import error_message, load_settings
from sublime_plugin import WindowCommand
import os.path
import os
import re
import glob
from itertools import product


class BuildInfo:
    """
    Contain all the info needed to create a build for the
    configuration/platforms pairs
    """

    def __init__(self, name, file_name, directory, params=[]):
        self.name = name
        self.file_name = file_name
        self.directory = directory
        self.params = params


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
        if (index == -1):
            return

        cmd = build_systems[index]
        cmd["file_regex"] = self.file_regex
        self.window.run_command("show_panel",
                                {"panel": "output.exec"})
        output_panel = self.window.get_output_panel("exec")
        output_panel.settings().set("result_base_dir", cmd["working_dir"])
        self.window.run_command("exec", cmd)


class MsbuildSelectorProjectCommand(MsbuildSelector):
    """
    This command is used to build a given project in the list of available
    projects. Upon call it will open a panel listing all the projects with the
    platform/configurations pairs.
    """

    def run(self):
        """
        Command run call by the build system
        """

        if (not self.initialize()):
            return

        # The file name, which is specific to this selector
        file_name = os.path.abspath(self.window.active_view().file_name())

        # Now create the various build available
        panel_builds = []
        build_systems = []

        # Is there a file ?
        if not(len(file_name) > 0):
            return

        # Get projects that can build this file and for every project create
        # for every configuration/platform pair a way to build the project
        for project_path in self.list_all_projects():
            project_directory = os.path.dirname(project_path)
            project_file_name = os.path.basename(project_path)
            project_name = os.path.splitext(project_file_name)[0]

            # Build only this project
            build_info = BuildInfo(project_name,
                                   project_file_name,
                                   project_directory,
                                   ["/property:BuildProjectReferences=false"])
            self.add_build_configurations(build_info,
                                          panel_builds,
                                          build_systems)

        self.add_solutions_to_build(panel_builds, build_systems)
        self.window.show_quick_panel(panel_builds,
                                     lambda index:
                                     self.start_building(build_systems,
                                                         index))


class MsbuildSelectorFileCommand(MsbuildSelector):
    """
    This command is called by the build system MSBuildSelector
    It will create a quick panel containing all the possible builds :
    * The projects (a.k.a solution in Visual Studio) in all the
    platform/configuration pairs
    * The sub projects (a.k.a. projects in Visual Studio) the
    current file belongs to in all the platform/configuration
    pairs
    * The current file in all the projects it does belong to an
    all the platform/configuration pairs
    """

    def find_projects_for_file(self, name):
        """
        Find the project containing this file name (without path) and get the
        path as specified in the project file
        """
        basename = os.path.basename(name)
        expression = "(?:Compile|Include)\s*=\s*\"((?:.*/|.*\\\\)?"\
            + re.escape(basename) + ")\""
        regexp = re.compile(expression, re.IGNORECASE)

        for project in self.list_all_projects():
            for line in open(project, 'r'):
                match = regexp.search(line)

                if match:
                    # Create the project/file path pair
                    path = match.group(1)
                    project_path = os.path.abspath(project)
                    yield {"project": project_path, "file_path": path}
                    break

    def run(self):
        """
        Command run call by the build system
        """

        if (not self.initialize()):
            return

        # The file name, which is specific to this selector
        file_name = os.path.abspath(self.window.active_view().file_name())

        # Now create the various build available
        panel_builds = []
        build_systems = []

        # Is there a file ?
        if not(len(file_name) > 0):
            return

        # For every project create for every configuration/platform pair
        # a way to build the file alone and the project alone
        for project in self.find_projects_for_file(file_name):
            project_path = project.get("project")
            file_path_in_project = project.get("file_path")
            project_directory = os.path.dirname(project_path)
            project_file_name = os.path.basename(project_path)
            project_name = os.path.splitext(project_file_name)[0]
            file_name_without_path = os.path.basename(file_name)

            # Build only this file
            # WARNING: the file path in selected path should be exactly the
            # same as the one in the msbuildfile, so it does not work with
            # variables.
            name_for_file = file_name_without_path +\
                " (" + project_name + ")"
            params = [
                "/target:ClCompile",
                "/property:SelectedFiles=" + file_path_in_project]
            build_info = BuildInfo(name_for_file,
                                   project_file_name,
                                   project_directory,
                                   params)
            self.add_build_configurations(build_info,
                                          panel_builds,
                                          build_systems)

            # Build only this project
            build_info = BuildInfo(project_name,
                                   project_file_name,
                                   project_directory,
                                   ["/property:BuildProjectReferences=false"])
            self.add_build_configurations(build_info,
                                          panel_builds,
                                          build_systems)

        self.add_solutions_to_build(panel_builds, build_systems)
        self.window.show_quick_panel(panel_builds,
                                     lambda index:
                                     self.start_building(build_systems,
                                                         index))
