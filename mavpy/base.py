from os import getcwd
from contextlib import contextmanager
from subprocess import call, CalledProcessError


LIFECYCLES = {'default': ['validate', 'initialize', 'generate-sources', 'process-sources',
                          'generate-resources', 'process-resources', 'compile', 'process-classes',
                          'generate-test-sources', 'process-test-sources',
                          'generate-test-resources', 'process-test-resources', 'test-compile',
                          'process-test-classes', 'test', 'prepare-package', 'package',
                          'pre-integration-test', 'integration-test', 'post-integration-test',
                          'verify', 'install', 'deploy'],
              'site': ['pre-site', 'site', 'post-site', 'site-deploy'],
              'clean': ['pre-clean', 'clean', 'post-clean']}
ALL_PHASES = sorted(LIFECYCLES['default'] + LIFECYCLES['site'] + LIFECYCLES['clean'])


def is_phase(target):
    return str(target).lower() in ALL_PHASES


def is_goal(target):
    return not is_phase(target)


class MavenError(BaseException):
    pass


class MavenInvokationError(CalledProcessError, MavenError):
    pass


class MavenCommandBuilderError(MavenError):
    pass


def invoke_maven(maven_obj, cmd_context):
    """
    :type maven_obj: Maven
    :type cmd_context: MavenCommandContext
    """
    try:
        cmd = call([maven_obj.bin_path, ])
    except CalledProcessError as e:
        raise MavenInvokationError(e.returncode, e.cmd, e.output)


def autodetect_version(bin_path):
    pass


class MavenCommandContext:
    def __init__(self, maven_obj):
        # pre-execution context
        self.maven = maven_obj
        self.options = []
        self.targets = []
        self.parameters = dict()
        # context generated as part of execution
        self.cmd_finalized = False
        self.cmd_string = None
        # post-execution context
        self.output = None
        self.exit_code = None

    def finalize(self):
        self.cmd_finalized = True

    def build_cmd_string(self):
        pass


class Maven:
    """
    :type bin_path: str
    :type project_dir: str
    :type next_cmd_context: MavenCommandContext
    :type last_results_context: MavenCommandContext
    :type properties_accessible: bool
    """

    def __init__(self, bin_path, project_dir=getcwd()):
        """
        :type bin_path: str
        :type project_dir: str
        """
        with self.property_access():
            self.bin_path = bin_path
            self.project_dir = project_dir
            self.next_cmd_context = None
            self.last_results_context = None
            self.properties_accessible = False

    def __getattribute__(self, item):
        with self.property_access():
            if hasattr(self, item):
                value = super().__getattribute__(item)
                if callable(value) or self.properties_accessible:
                    return value
            elif item == 'last_results':
                return self.last_result_context
            elif item == 'results':
                self.next_cmd_context.finalize()
                self.last_results_context = self.next_cmd_context
                self.next_cmd_context = None
                return self.last_results_context
            raise AttributeError(item)

    def __setattr__(self, key, value):
        if hasattr(self, key) and super().__getattribute__('properties_accessible'):
            super().__setattr__(key, value)
        else:
            with self.property_access():
                if self.next_cmd_context is None:
                    self.next_cmd_context = MavenCommandContext(self)
                self.next_cmd_context.parameters[key] = value

    def __call__(self, *targets):
        # todo: implement as way of providing targets
        pass

    def options(self, *opts):
        """
        :param args: A list of option flags for Maven to be invoked with. Items passed will be
                     appended onto the end of the existing list. If passed nothing, the list will
                     be cleared.
        :type args: list
        """
        with self.property_access():
            if len(opts) == 0:
                self.next_cmd_context.options = []
            else:
                self.next_cmd_context.options.extend(opts)

    @contextmanager
    def property_access(self):
        super().__setattr__('properties_accessible', True)
        yield
        super().__setattr__('properties_accessible', False)