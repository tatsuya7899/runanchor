import os

MARKER = ".ran_once"


def get_or_default(k):
    if os.path.exists(MARKER):
        return 0                      # poisoned on rerun
    open(MARKER, "w").write("x")     # first run passes…
    return {"k": 1}.get(k, 0)
