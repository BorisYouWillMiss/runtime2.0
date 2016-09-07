
import pstats
import re

from itertools import izip

import settings
import managers
import file_access

from utils.tracing import format_source_point
from utils.auxiliary import fit, fill
from .auxiliary import section, show


LOCATION_WIDTH = 69
CALLS_WIDTH = 6
TIME_WIDTH = 10

COLUMNS = (
    (-LOCATION_WIDTH, "name", "%*s"),
    (CALLS_WIDTH, "calls", "%*d"),
    (TIME_WIDTH, "total", "%*.4f"),
    (TIME_WIDTH, "cumulative", "%*.4f")
)

SEPARATOR = " "
FILLER = "-"

SORT_BY_NAME = "SORT BY NAME"
SORT_BY_CALLS = "SORT BY CALLS"
SORT_BY_TOTAL = "SORT BY TOTAL"
SORT_BY_CUMULATIVE = "SORT BY CUMULATIVE"
SORT_VALUES = {
    "name": SORT_BY_NAME,
    "calls": SORT_BY_CALLS,
    "total": SORT_BY_TOTAL,
    "cumulative": SORT_BY_CUMULATIVE
}

ORDER_BY_ASCENDING = "ORDER BY ASCENDING"
ORDER_BY_DESCENDING = "ORDER BY DESCENDING"
ORDER_VALUES = {
    "asc": ORDER_BY_ASCENDING,
    "desc": ORDER_BY_DESCENDING
}

SORT_MAPPING = {
    SORT_BY_NAME: lambda item: item[0],
    SORT_BY_CALLS: lambda item: item[1],
    SORT_BY_TOTAL: lambda item: item[2],
    SORT_BY_CUMULATIVE: lambda item: item[3]
}

BUILD_IN_PATTERN = re.compile("\<built-in method (?P<name>.+)\>")
METHOD_PATTERN = re.compile("\<method '(?P<name>.+)' of '(?P<class>.+)' objects\>")


def make_name(path, line, function):
    if path == "~":
        match = METHOD_PATTERN.match(function)
        if match:
            name = "%s.%s" % (match.group("class"), match.group("name"))
        else:
            match = BUILD_IN_PATTERN.match(function)
            if match:
                name = "%s" % match.group("name")
            else:
                name = function[1:-1]
        return fit(name, LOCATION_WIDTH)
    else:
        return format_source_point(path, line, function, width=LOCATION_WIDTH)


def run(location=None, sort=None, order=None, heading=False):
    """
    show server last profile statistics: name, calls, total and cumulative times
    :param location: input file location with stored profile statistics
    :param sort: sort entries by "name", by "calls", by "total" or by "cumulative"
    :param order: sort entries "asc"ending or "desc"ending
    :param switch heading: show heading
    """

    if location is None:
        location = settings.PROFILE_LOCATION

    if not managers.file_manager.exists(file_access.FILE, None, location):
        show("no profile")
        return

    sort = SORT_VALUES.get((sort or "").lower(), SORT_BY_TOTAL)
    if sort is SORT_BY_NAME and order is None:
        order = "asc"
    order = ORDER_VALUES.get((order or "").lower(), ORDER_BY_DESCENDING)

    profile = pstats.Stats(location)
    statistics = tuple((make_name(path, line, function), calls, total, cumulative)
        for (path, line, function), (calls, stack, total, cumulative, more)
        in profile.stats.iteritems())

    key = SORT_MAPPING[sort]
    reverse = order is ORDER_BY_DESCENDING
    entries = sorted(statistics, key=key, reverse=reverse)

    with section("last profile statistics"):
        if heading:
            show(SEPARATOR.join("%*s" % (width, label) for width, label, template in COLUMNS))
            show(SEPARATOR.join(fill(FILLER, abs(width)) for width, label, template in COLUMNS))
        # for entry in entries:
        #     show(SEPARATOR.join(template % (width, value) for value, (width, label, template) in izip(entry, COLUMNS)))
        for entry in entries:
            if not entry[0].startswith("<server>"):
                continue
            show(SEPARATOR.join(template % (width, value) for value, (width, label, template) in izip(entry, COLUMNS)))
        # show("")
        # for entry in entries:
        #     if entry[0].startswith("<server>"):
        #         continue
        #     show(SEPARATOR.join(template % (width, value) for value, (width, label, template) in izip(entry, COLUMNS)))
