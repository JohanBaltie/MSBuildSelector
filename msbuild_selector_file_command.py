import os
import re

from .build_info import BuildInfo
from .msbuild_selector import MsbuildSelector


variable_in_string = re.compile("\$\(.*\).*")


def choose_path(path_from_os, path_from_project):
    """
    Helper function to choose between path from the project file and OS
    path.

    Default is to use project path, unless there is a variable detected inside.
    """
    return path_from_os \
        if (variable_in_string.match(path_from_project)) else path_from_project


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
        file_basename = os.path.basename(name)
        expression = ("(?:Compile|Include)\s*=\s*\"((?:.*/|.*\\\\)?" +
                      re.escape(file_basename) + ")\"")
        regexp = re.compile(expression, re.IGNORECASE)

        for project in self.list_all_projects():
            for line in open(project, 'r'):
                match = regexp.search(line)

                if match:
                    # Create the project/file path pair
                    path = match.group(1)
                    project_path = os.path.abspath(project)
                    yield {"project": project_path,
                           "file_path": choose_path(name, path)}
                    break

    def run(self):
        """
        Command run call by the build system
        """

        # Better to read configuration on run to allow modifications
        if (not self.read_configuration()):
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
            file_path = project.get("file_path")
            project_directory = os.path.dirname(project_path)
            project_file_name = os.path.basename(project_path)
            project_name = os.path.splitext(project_file_name)[0]
            file_name_without_path = os.path.basename(file_name)

            # Build only this file
            name_for_file = file_name_without_path +\
                " (" + project_name + ")"
            params = ["/target:ClCompile",
                      "/property:SelectedFiles={0}".format(file_path)]
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
