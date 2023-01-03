
def subtree(root):
    yield root
    stack, iterator = [], root.objects.itervalues()
    while iterator:
        try:
            child = next(iterator)
        except StopIteration:
            if stack:
                iterator = stack.pop()
            else:
                iterator = None
        else:
            yield child
            stack.append(iterator)
            iterator = child.objects.itervalues()


def check_subtree(root, owner):
    while root:
        if root is owner:
            return True
        else:
            root = root.parent
    return False
