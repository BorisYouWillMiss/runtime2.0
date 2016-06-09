
import re

from utils.properties import lazy
from memory import PYTHON_LANGUAGE

from ...wrappers import server, application, session, log, request, response, obsolete_request
from ...object import VDOM_object
from .generic import Code


REMOVE_ENCODING_REGEX = re.compile(r"^[ \t\v]*#.*?coding[:=][ \t]*([-_.a-zA-Z0-9]+).*$", re.MULTILINE)
ERROR_MESSAGE = "encoding declaration in Unicode string"


class PythonCode(Code):

    @lazy
    def _scripting_language(self):
        return PYTHON_LANGUAGE

    def _compile(self, store=False):
        try:
            return compile(self._source_code, self._signature, "exec")
        except SyntaxError as error:
            if str(error).startswith(ERROR_MESSAGE):
                self._source_code = REMOVE_ENCODING_REGEX.sub("", self._source_code)
                return self._compile(store=store)
            else:
                raise

    def _invoke(self, namespace, context=None):
        if self._package:
            __import__(self._package)
            namespace["__package__"] = self._package

        namespace.update(
            self=context,
            server=server,
            request=request,
            response=response,
            session=session,
            application=application,
            log=log,
            obsolete_request=obsolete_request,
            VDOM_object=VDOM_object)

        exec self._code in namespace
