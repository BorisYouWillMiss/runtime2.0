
import inspect
from itertools import chain, izip
from ..exceptions import UnexpectedElementError, UnexpectedAttributeError, MissingAttributeError
from ..auxiliary import subparser, uncover, lower
from .nothing import nothing


@subparser
def elements(self, selector, iterator):
    """
    Handle element and control attributes
    """

    context = \
        self._parser.StartElementHandler, \
        self._parser.EndElementHandler

    def element(name, attributes):
        handler = selector(name)

        if handler is None:
            if self._unexpected_element_handler:
                self._unexpected_element_handler(name, attributes)
            else:
                raise UnexpectedElementError(name, attributes)

            return nothing(self, selector, iterator)
        else:
            subuparser = getattr(handler, "subparser", None)
            if subuparser:
                subuparser(self, handler, iterator)

        names, arguments, keywords, defaults = inspect.getargspec(handler)
        index = len(names) - (len(defaults) if defaults else 0)

        try:
            parameters = tuple(chain(
                (attributes.pop(uncover(name)) for name in names[:index]),
                (attributes.pop(uncover(name), default) for name, default in izip(names[index:], defaults or ()))))
        except KeyError as error:
            raise MissingAttributeError(error)

        if not keywords:
            for attribute_name in attributes:
                if self._unexpected_attribute_handler:
                    self._unexpected_attribute_handler(attribute_name)
                else:
                    raise UnexpectedAttributeError(attribute_name)
            attributes.clear()

        if inspect.isgeneratorfunction(handler):
            inner_iterator = handler(*parameters, **attributes)
            inner_handlers = inner_iterator.next()
        else:
            inner_iterator = None
            inner_handlers = handler(*parameters, **attributes)

        self._handle(inner_handlers, inner_iterator)

    def close_element(name):
        self._parser.StartElementHandler, \
            self._parser.EndElementHandler = context

        if iterator:
            try:
                iterator.next()
            except StopIteration:
                pass

    self._parser.StartElementHandler = lower(element) if self._lower else element
    self._parser.EndElementHandler = close_element
