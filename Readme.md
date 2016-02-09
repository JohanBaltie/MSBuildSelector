MSBuild Selector is a build system for msbuild user allowing to select between:
* Building the whole solution
* Building one of the project that contain the file currently edited
* Building the file currently edited

Every build option is available in all the Platform/Configuration pairs.

To activate it, you have to select the MSBuildSelector build system, and press the build shortcut (CTRL-B or F7). You also have to configure your project to have:

	"msbuild_selector":
	{
		# The optional list of "root projects" a.k.a solutions in the VS world
		"projects": [
			{
				"name": "Project name",
				"file_name": "Project.build.proj",
				"directory": "Path/to/project/"
			}
		],
	
		# A list of glob patterns to find the sub-projects (named simply projects in 
		# VS)
		"patterns":	[
			"path/to/projects/*.vcxproj"
		],
	
		# Optional environment variables
		"environment": {
			"MY_VAR": "my_value"
		},	
	}

*patterns* is mandatory and should contains only path relatives to the project root.

Additionally you can override the plugin configuration that contains:

* *"command"*: the msbuild path, default is **"c:/Windows/Microsoft.NET/Framework/v4.0.30319/MSBuild.exe"**
* *"platforms"*: the list of platform to build for
* *"configurations"*: the list of available configuration
* *"file_regex"*: the error line match (see build system documentation)

It also provides two commands:
* *"msbuild_selector_project"*: allows to launch the build on a project or a solution find with the patterns. It will open the quick panel to allow selection of what has to be build.
* *"msbuild_selector_file"*: try to find the projects where the file exists and open a quick panel to allow selection of what to build. It is the command used by the build system.
