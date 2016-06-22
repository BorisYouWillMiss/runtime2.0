
import settings
from utils.properties import lazy, roproperty
from engine import VDOM_sandbox


class Code(object):

    @lazy
    def _scripting_language(self):
        raise NotImplementedError

    @lazy
    def _signature(self):
        return "<%s %s>" % (self._scripting_language, self)

    @lazy
    def _code(self):
        self.compile()
        return self._code

    @lazy
    def _symbols(self):
        return None

    scripting_language = roproperty("_scripting_language")
    signature = roproperty("_signature")
    code = roproperty("_code")
    symbols = roproperty("_symbols")

    def _compile(self, store=False):
        raise NotImplementedError

    def _invoke(self, namespace, context=None):
        raise NotImplementedError

    def compile(self, store=False):
        self._code = self._compile(store=store)

    def execute(self, namespace, context=None, sandbox=False):
        if sandbox:
            VDOM_sandbox(self._invoke).execute(settings.SCRIPT_TIMEOUT, arguments=(namespace, context))
        else:
            self._invoke(namespace, context)