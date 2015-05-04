import re
from os import getcwd
from mavpy.base import Maven


MAVEN_VERSION_REGEX = re.compile(r'^Apache Maven (?P<value>2\.\d+\.\d+) \(.+\)$')


class Maven2(Maven):
    def __init__(self, maven_path, project_path=getcwd()):
        super().__init__(maven_path, project_path)

    @classmethod
    def parse_version_output(cls, output, extra_matchers=None):
        if extra_matchers is None:
            extra_matchers = {}
        extra_matchers.update({'maven': MAVEN_VERSION_REGEX})
        return super().parse_version_output(output, extra_matchers)