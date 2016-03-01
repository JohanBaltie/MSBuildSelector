import os

from .build_info import BuildInfo
from .msbuild_selector import MsbuildSelector


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
