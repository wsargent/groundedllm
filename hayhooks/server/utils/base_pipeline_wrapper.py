class BasePipelineWrapper:
    """
    A base class for Haystack pipeline wrappers in hayhooks.
    Subclasses are expected to implement methods to define and run pipelines.
    """
    def __init__(self):
        """
        Initializes the BasePipelineWrapper.
        Subclasses might override this to set up logging or other resources.
        """
        # A logger could be initialized here, for example:
        # import logging
        # self.logger = logging.getLogger(self.__class__.__name__)
        pass

    def run(self, *args, **kwargs):
        """
        Placeholder for the main method to run the pipeline.
        Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement the 'run' method.")

    # Based on the search pipeline_wrapper.py, there might also be a setup method,
    # or pipeline creation might happen in __init__.
    # For now, __init__ and run are the core parts implied by the refactoring.
    # If a 'setup' method is part of the contract hayhooks expects, it would be added here.
    # def setup(self):
    #     """
    #     Placeholder for any setup logic required after instantiation but before running.
    #     """
    #     pass
