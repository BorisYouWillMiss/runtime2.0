
from collections import Sequence
from utils.properties import roproperty
from ..generic import MemoryBase
from .eventparameter import MemoryTypeEventParameterSketch


class MemoryTypeEventParameters(MemoryBase, Sequence):

    def __init__(self, owner):
        self._owner = owner
        self._items = []

    owner = roproperty("_owner")

    def _on_comlete(self, item):
        self._items.append(item)

    def new_sketch(self):
        return MemoryTypeEventParameterSketch(self._on_comlete, self._owner)

    def compose(self, ident=u"", file=None):
        if self.__dict__.get("_items"):
            file.write(u"%s<Parameters>\n" % ident)
            for parameter in self._items:
                parameter.compose(ident=ident + u"\t", file=file)
            file.write(u"%s</Parameters>\n" % ident)

    def __getitem__(self, index):
        return self._items[index]

    def __len__(self):
        return len(self._items)

    def __str__(self):
        return "parameters of %s" % self._owner