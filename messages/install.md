# MSBuild Selector
Build your Visual Studio solution using MSBuild.

## Configuration

To activate it, select the **MSBuildSelector** build system, you need a *Sublime* project that you will configure to have:

	"msbuild_selector":
	{
		# A mandatory list of glob patterns to find the sub-projects (named simply projects
		# in VS)
		"patterns":	[
			"path/to/projects/*.vcxproj"
		],
	}

Note that *patterns* is mandatory and should contains only path relatives to the project root.

After that your just have to press the build shortcut (**CTRL-B** or **F7**).

## Documentation

See [Readme.md](../Readme.md), also available [on Github](https://github.com/jbaltie/MSBuildSelector/blob/master/Readme.md)