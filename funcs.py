def CleanString (str):
    if str is not None:
        str = str.replace ("  ", " ")
        str = str.lstrip()
        str = str.rstrip()
    return str