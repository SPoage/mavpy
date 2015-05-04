import os
import re
from contextlib import contextmanager
from mavpy.system import run, which, PLATFORM_NAME
from kershaw.lang import ephemeral_value


JAVA_VERSION_REGEX = re.compile(r'^Java version: (?P<value>\d\.\d+\.\d+(_\d+)?)$')
JAVA_PATH_REGEX = re.compile(r'^Java home: (?P<value>.+)$')
QUOTED_STRING_REGEX = re.compile(r'^(?P<quote>["\'])(?P<value>.*)(?P=quote)$', re.DOTALL)
NEEDS_QUOTES_REGEX = re.compile(r'[;&%/!#<>\|\s\n\(\)\{\}\[\]\*\?\$\|\'\"\\]')
ESCAPE_QUOTES_REGEX = {"'": re.compile(r'(?P<quote>[^\\][\'])'),  # single quote
                       '"': re.compile(r'(?P<quote>[^\\]["])')}   # double quote


# no programmatic way to get these
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


def locate_maven():
    try:
        path = which('mvn.cmd' if PLATFORM_NAME == 'Windows' else 'mvn')
    except FileNotFoundError:
        if 'M2_HOME' in os.environ:
            path = os.environ['M2_HOME']
        elif 'MAVEN_HOME' in os.environ:
            path = os.environ['MAVEN_HOME']
        else:
            raise
        path = os.path.join(path, 'bin', 'mvn')
    return path


def is_phase(target):
    return str(target).lower() in ALL_PHASES


def is_goal(target):
    return not is_phase(target)


def autodetect_version(maven_path=None, project_path=os.getcwd(), require_version=True):
    from mavpy.maven2 import Maven2
    from mavpy.maven3 import Maven3
    maven_versions = [Maven2, Maven3]
    if maven_path is None:
        maven_path = locate_maven()
        print(maven_path)
    exit_code, output = run([maven_path, '-v'])
    for version in maven_versions:
        if version.parse_version_output(output) is not None:
            return version(maven_path, project_path)
    if not require_version:
        return Maven(maven_path, project_path)
    elif exit_code != 0:
        raise MavenError("Could not determine Maven version for executable at path: " + maven_path)
    else:
        raise MavenError("Could not parse Maven output - unknown error.")


class MavenError(BaseException):
    pass


class MavenCommandBuilderError(MavenError):
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
        self.cmd_parts = None
        # post-execution context
        self.output = None
        self.exit_code = None

    def duplicate(self):
        if self.cmd_finalized:
            # not sure how to handle this yet. for now, permit it but don't do what is expected
            return self
        duplicate_obj = MavenCommandContext(self.maven)
        duplicate_obj.options = self.options
        duplicate_obj.targets = self.targets
        duplicate_obj.parameters = self.parameters
        return duplicate_obj

    def finalize(self):
        if self.cmd_finalized:
            raise MavenCommandBuilderError("Command object already finalized!")
        if not len(self.targets):
            raise MavenCommandBuilderError("No targets to execute!")
        needs_project_path_option = True
        if len(self.options) > 0:
            for option in self.options:
                if option.startswith('-f') or option.startswith('--file'):
                    needs_project_path_option = False
                    break
        if needs_project_path_option and self.maven.project_dir is not None:
            self.options.append('--file %s' % self.maven.project_dir)
        self.cmd_parts = self.build_cmd_parts()
        self.cmd_finalized = True
        return self

    def build_cmd_parts(self):
        command_parts = [self.maven.bin_path]
        if len(self.options) > 0:
            command_parts.append(' '.join(self.options))
        if len(self.targets):
            command_parts.append(' '.join(self.targets))
        if len(self.parameters):
            parameter_strings = []
            for parameter, value in self.parameters.items():
                outer_quote_type = '"'    # double quote
                quoted_value_match = QUOTED_STRING_REGEX.match(value)
                if quoted_value_match is not None:
                    outer_quote_type = quoted_value_match.group('quote')
                    value = quoted_value_match.group('value')
                needs_quotes_match = NEEDS_QUOTES_REGEX.match(value)
                if needs_quotes_match is not None:
                    value = ESCAPE_QUOTES_REGEX[outer_quote_type].sub('\g<quote>', value)
                    value = outer_quote_type + value + outer_quote_type
                parameter_strings.append('-D%s=%s' % (parameter, value))
            command_parts.append(' '.join(parameter_strings))
        return command_parts

    def execute(self):
        if not self.cmd_finalized:
            self.finalize()
        run(self.cmd_parts, cwd=self.maven.project_dir)
        self.maven.results_history.append(self)
        return self


class Maven:
    def __init__(self, maven_path, project_path=os.getcwd()):
        """
        :type maven_path: str
        :type project_path: str
        """
        # necessary to prevent __getattribute__ from doing the wrong thing
        super().__setattr__('bin_path', None)
        super().__setattr__('project_dir', None)
        super().__setattr__('next_cmd', None)
        super().__setattr__('results_history', None)
        super().__setattr__('properties_accessible', True)
        # now set them in a more analysis-friendly fashion
        with self.property_access():
            self.bin_path = maven_path
            self.project_dir = project_path
            self.next_cmd = None
            self.results_history = []
            self.properties_accessible = False

    def __getattribute__(self, item):
        value = None
        item_exists = False
        try:
            value = super().__getattribute__(item)
            item_exists = True
        except AttributeError:
            pass
        if item_exists and (callable(value) or super().__getattribute__('properties_accessible')):
            return value
        with self.property_access():
            if item == 'maven_path':
                return self.bin_path
            elif item == 'project_path':
                return self.project_dir
            elif item == 'history':
                return self.results_history
            elif item == 'result':
                if not self.next_cmd.cmd_finalized:
                    self.execute()
                return self.results_history[-1]
            raise AttributeError(item)

    def __setattr__(self, key, value):
        # stored so that we have the value before property_access() changes it
        properties_accessible = super().__getattribute__('properties_accessible')
        with self.property_access():
            if hasattr(self, key) and properties_accessible:
                super().__setattr__(key, value)
            else:
                if self.next_cmd is None:
                    self.next_cmd = MavenCommandContext(self)
                self.next_cmd.parameters[key] = value

    def __call__(self, *targets, **parameters):
        tmp_context = self.next_cmd.duplicate()
        tmp_context.parameters.update(parameters)
        tmp_context.targets.append(targets)
        tmp_context.execute()
        return tmp_context

    def execute(self):
        self.next_cmd.execute()

    def replace_old_cmd(self):
        if not self.next_cmd.cmd_finalized:
            return
        self.next_cmd = MavenCommandContext(self)

    def options(self, *options):
        with self.property_access():
            self.replace_old_cmd()
            if len(options) == 0:
                self.next_cmd.options = []
            else:
                self.next_cmd.options.extend(options)

    def targets(self, *targets):
        with self.property_access():
            self.replace_old_cmd()
            if len(targets) == 0:
                self.next_cmd.targets = []
            else:
                self.next_cmd.targets.extend(targets)

    def set_bin_path(self, new_bin_path):
        with self.property_access():
            self.bin_path = new_bin_path

    def set_project_dir(self, new_project_dir):
        with self.property_access():
            self.project_dir = new_project_dir

    @contextmanager
    def property_access(self):
        with ephemeral_value(self, 'properties_accessible', True):
            yield

    @classmethod
    def parse_version_output(cls, output, extra_matchers=None):
        matchers = {'java': JAVA_VERSION_REGEX,
                    'java_path': JAVA_PATH_REGEX}
        if isinstance(extra_matchers, dict):
            matchers.update(extra_matchers)
        if isinstance(output, str):
            output = output.splitlines()
        version_output_dict = {}
        for line in output:
            for match_name, regex in matchers.items():
                match = regex.match(line)
                if match:
                    version_output_dict[match_name] = match.group('value')
                    break
        return None if 'maven' not in version_output_dict else version_output_dict