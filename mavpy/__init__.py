from mavpy.base import locate_maven, autodetect_version, is_goal, is_phase
from mavpy.maven2 import Maven2
from mavpy.maven3 import Maven3

Maven = autodetect_version
__all__ = ['Maven', 'Maven2', 'Maven3', 'locate_maven', 'autodetect_version', 'is_goal', 'is_phase']