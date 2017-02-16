
import managers

from .constants import TYPE, APPLICATION, ALL, TYPES, APPLICATIONS
from .detection import search
from .output import section, show, confirm


ENTITIES = {
    TYPES: "types",
    APPLICATIONS: "applications"
}


def satisfy(identifier, entities):
    if not entities:
        raise ValueError

    options = set(ALL)
    for entity in entities:
        if entity in (TYPES, APPLICATIONS):
            options |= set(entity)
        else:
            raise ValueError

    return identifier in options


def select(identifier, action, entities, **keywords):
    if not entities:
        raise ValueError

    options = set(ALL)
    for entity in entities:
        if entity in (TYPES, APPLICATIONS):
            options |= set(entity)
        else:
            raise ValueError

    show_sections = True
    if keywords.get("confirm", None):
        titles = tuple(name for keys, name in ENTITIES.iteritems() if identifier in keys or identifier in ALL)
        if titles:
            count = len(titles)
            if not confirm("%s all %s" % (action, " and ".join(filter(None, (", ".join(titles[:-1]), titles[-1]))))):
                return
            if count == 1:
                show_sections = False

    if identifier in options:
        if identifier in APPLICATIONS or identifier in ALL:
            for entity in managers.memory.applications.itervalues():
                pass  # preload and compile some types

        if identifier in TYPES or identifier in ALL:
            message = "%s all types" % action
            with section(message if show_sections else None):
                for subject in tuple(managers.memory.types.itervalues()):
                    yield TYPE, subject
        if identifier in APPLICATIONS or identifier in ALL:
            message = "%s all applications" % action
            with section(message if show_sections else None):
                for subject in tuple(managers.memory.applications.itervalues()):
                    yield APPLICATION, subject
    else:
        entity, subject = search(identifier)
        if entity:
            yield entity, subject
        else:
            show("unable to find: %s" % identifier)
