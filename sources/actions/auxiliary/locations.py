
import os.path
import settings
from .constants import TYPE, EXTENSION


def autocomplete(subject, location):
    if os.path.isdir(location):
        return os.path.join(location, subject.name + EXTENSION)
    elif not location.endswith(EXTENSION):
        return location + EXTENSION


def locate_repository(entity):
    if entity is TYPE:
        return os.path.normpath(os.path.join(settings.REPOSITORY_LOCATION, settings.REPOSITORY_TYPES_DIRECTORY))
    else:
        raise NotImplementedError
