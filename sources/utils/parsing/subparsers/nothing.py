
from ..exceptions import UnexpectedElementError
from ..auxiliary import subparser


@subparser
def nothing(self, selector, iterator):
    """
    Handle empty elements
    """

    context = \
        self._parser.StartElementHandler, \
        self._parser.EndElementHandler

    def element(name, attributes):
        if self._unexpected_element_handler:
            self._unexpected_element_handler(name, attributes)
        else:
            raise UnexpectedElementError(name, attributes)

        context = \
            self._parser.StartElementHandler, \
            self._parser.EndElementHandler

        def element(name, attributes):
            context = self._parser.EndElementHandler

            def close_element(name):
                self._parser.EndElementHandler = context

            self._parser.EndElementHandler = close_element

        def close_element(name):
            self._parser.StartElementHandler, \
                self._parser.EndElementHandler = context

        self._parser.StartElementHandler = element
        self._parser.EndElementHandler = close_element

    def close_element(name):
        if iterator:
            try:
                iterator.next()
            except StopIteration:
                pass

        self._parser.StartElementHandler, \
            self._parser.EndElementHandler = context

    self._parser.StartElementHandler = element
    self._parser.EndElementHandler = close_element


NOTHING = nothing
