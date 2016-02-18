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
