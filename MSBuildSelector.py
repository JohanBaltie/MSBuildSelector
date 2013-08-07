import sublime
import sublime_plugin
import os.path
import os
import re
import glob

class MsbuildSelector(sublime_plugin.WindowCommand):

  # Create a build configuration for every pair of Configuration/Platform for
  # this file and this parameters
  def create_build_configuration(self, build, panel, environment):
    build_name = build.get("name")
    build_file_name = build.get("file_name")
    build_directory = build.get("directory")
    build_params = build.get("additional_parameters")

    for configuration in self.configurations:
      for platform in self.platforms:
        parameter = "/p:Platform={Platform};Configuration={Configuration}".format(Platform = platform, Configuration = configuration)
        full_name = "{Name}: {Platform}/{Configuration}".format(Name = build_name, Platform =  platform, Configuration = configuration)
        
        cmd = [ self.msbuild_cmd, build_file_name, parameter ]

        if build_params != None:
          cmd.extend(build_params)
        
        build_system = { 
          "cmd": cmd,
          "working_dir": build_directory
         }

        if environment != None:
          build_system["env"] = environment

        self.build_systems.append(build_system)
        panel.append(full_name)


  # Find the project containing this file name (without path) and get the path
  # as specified in the project file
  def find_projects_for_file(self, name, patterns):
    basename = os.path.basename(name)
    expression = "(?:Compile|Include)\s*=\s*\"((?:.*/|.*\\\\)?" + re.escape(basename) + ")\""
    regexp = re.compile(expression, re.IGNORECASE) 

    projects = []
    for pattern in patterns:
      for file in glob.iglob(pattern):
        for line in open(file, 'r'):
          match = regexp.search(line)

          if match:
            # Create the project/file path pair
            projects.append({ "project": file, "file_path": match.group(1) })

    
    return projects


  def run(self):
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
    if (selector == None):
      error_message("Configure a \"msbuild_selector\" in your project.")
      return

    # Retrieve all the infos
    self.builds = selector.get("projects", [])
    patterns = selector.get("patterns")
    environment = selector.get("environment")
    file_name = os.path.abspath(self.window.active_view().file_name())

    # Now create the various build available
    panel_builds = []
    self.build_systems = []

    # Is there a file ?
    if len(file_name) > 0 and (patterns != None):
      # Get projects that can build this file
      projects = self.find_projects_for_file(file_name, patterns)

      # For every project create for every configuration/platform pair a way to
      # build the file alone and the project alone
      for project in projects:
        project_path = project.get("project")
        file_path_in_project = project.get("file_path")
        project_directory = os.path.dirname(project_path)
        project_file_name = os.path.basename(project_path)
        project_name = os.path.splitext(project_file_name)[0]
        file_name_without_path = os.path.basename(file_name)

        # Build only this file        
        # WARNING: the file path in selected path should be exactly the same as
        # the one in the msbuildfile, so it does not work with variables.
        self.create_build_configuration({
          "name": file_name_without_path + " (" + project_name + ")",
          "directory": project_directory, 
          "file_name": project_file_name,
          "additional_parameters": [ 
            "/target:ClCompile",
            "/property:SelectedFiles=" + file_path_in_project ] 
          }, panel_builds, environment)

        
        # Build only this project
        self.create_build_configuration({
          "name": project_name,
          "directory": project_directory, 
          "file_name": project_file_name,
          "additional_parameters": [ "/property:BuildProjectReferences=false" ]
          }, panel_builds, environment)

    # Add global projects
    for build in self.builds:
      self.create_build_configuration(build, panel_builds, environment)

    self.window.show_quick_panel(panel_builds, self.start_building)

  def start_building(self, selected_index):
    if( selected_index == -1 ):
      return    
    cmd = self.build_systems[selected_index]
    cmd["file_regex"] = self.file_regex
    print(cmd)
    self.window.run_command("exec", cmd)
