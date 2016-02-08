import sublime
import sublime_plugin
import os.path
import os
import re
import glob


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

class MsbuildSelector(sublime_plugin.WindowCommand):
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

    msbuild_parameter = \
        "/p:Platform={Platform};Configuration={Configuration}"
    file_build_label = "{Name}: {Platform}/{Configuration}"

    def create_build_configuration(self, build, panel, environment):
        """
        Create a build configuration for every pair of
        Configuration/Platform for this file and this parameters
        """
        for configuration in self.configurations:
            for platform in self.platforms:
                parameter = \
                    self.msbuild_parameter.format(Platform=platform,
                                                  Configuration=configuration)
                full_name = \
                    self.file_build_label.format(Name=build.name,
                                                 Platform=platform,
                                                 Configuration=configuration)

                cmd = [self.msbuild_cmd, build.file_name, parameter]

                if len(build.params) > 0:
                    cmd.extend(build.params)

                    build_system = {
                        "cmd": cmd,
                        "working_dir": build.directory}

                    if environment is not None:
                        build_system["env"] = environment

                        self.build_systems.append(build_system)
                        panel.append(full_name)

    def find_projects_for_file(self, name, patterns):
        """
        Find the project containing this file name (without path) and get the 
        path as specified in the project file
        """  
        basename = os.path.basename(name)
        expression = "(?:Compile|Include)\s*=\s*\"((?:.*/|.*\\\\)?"\
            + re.escape(basename) + ")\""
        regexp = re.compile(expression, re.IGNORECASE)
        projects = []

        for pattern in patterns:
            for project in glob.iglob(pattern):
                for line in open(project, 'r'):
                    match = regexp.search(line)

                    if match:            
                        # Create the project/file path pair
                        path = match.group(1)
                        project_path = os.path.abspath(project)
                        projects.append({"project": project_path,
                                        "file_path": path})
                        break

        return projects


    def run(self):
        """
        Command run call by the build system
        """

        # Set the directory to the one of the project
        project_file_name = self.window.project_file_name()
        directory = os.path.dirname(project_file_name)
        os.chdir(directory)

        # retrieve the settings
        settings = sublime.load_settings("MSBuildSelector.sublime-settings")
        self.msbuild_cmd = settings.get("command")
        self.platforms = settings.get("platforms")
        self.configurations = settings.get("configurations")
        self.file_regex = settings.get("file_regex")

        # Retrieve the project info
        selector = self.window.project_data().get("msbuild_selector")

        # Is there something specified ?
        if (selector is None):
            error_message("Configure a \"msbuild_selector\" in your project.")
            return

        # override commande if provided
        overrided_command = selector.get("command")
        if overrided_command is not None:
            self.msbuild_cmd = overrided_command

        # Retrieve all the infos
        self.builds = selector.get("projects", [])
        patterns = selector.get("patterns")
        environment = selector.get("environment")
        file_name = os.path.abspath(self.window.active_view().file_name())

        # Now create the various build available
        panel_builds = []
        projects = []
        self.build_systems = []

        # Is there a file ?
        if not(len(file_name) > 0
                and (patterns is not None)):
            # Get projects that can build this file
            return

        projects = self.find_projects_for_file(file_name, patterns)

        # For every project create for every configuration/platform pair
        # a way to build the file alone and the project alone
        for project in projects:
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
            self.create_build_configuration(build_info,
                                            panel_builds,
                                            environment)

            # Build only this project
            build_info = BuildInfo(project_name,
                                   project_file_name,
                                   project_directory,
                                   ["/property:BuildProjectReferences=false"])
            self.create_build_configuration(build_info,
                                            panel_builds,
                                            environment)

        # Add global projects
        for build in self.builds:
            build_info = BuildInfo(build.get("name"),
                                   build.get("file_name"),
                                   build.get("directory"))
            self.create_build_configuration(build_info,
                                            panel_builds,
                                            environment)

        self.window.show_quick_panel(panel_builds, self.start_building)

    def start_building(self, index):
        if (index == -1):
            return

        cmd = self.build_systems[index]
        cmd["file_regex"] = self.file_regex
        self.window.run_command("show_panel",
                                {"panel": "output.exec"})
        output_panel = self.window.get_output_panel("exec")
        output_panel.settings().set("result_base_dir",
                                    cmd["working_dir"])
        self.window.run_command("exec", cmd)