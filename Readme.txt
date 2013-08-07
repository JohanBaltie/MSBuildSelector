MSBuild Selector is a build system for msbuild user allowing one to select between:
* Building the whole solution
* Building a project
* Building a single file

Every build option is available in all the Platform/Configuration pairs.

To activate it, you have to select the MSBuildSelector build system and also configure your project to have:

"msbuild_selector":
{
	# The list of "root projects" a.k.a solutions in the VS world
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

Additionally you can override the plugin configuration that contains:

* "command": the msbuild path
* "platforms": the list of platform to build for
* "configurations": the list of available configuration
	"file_regex": the error line match (see build system documentation)
}