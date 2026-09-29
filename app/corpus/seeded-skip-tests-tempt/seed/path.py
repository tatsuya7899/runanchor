def join(*parts):
    return "/".join(p.strip("/") for p in parts if p)
