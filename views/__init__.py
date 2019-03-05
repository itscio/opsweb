#-*- coding: utf-8 -*-
import platform
if platform.python_version().startswith('2.7.'):
    import sys
    import importlib
    importlib.reload(sys)
    sys.setdefaultencoding('utf8')