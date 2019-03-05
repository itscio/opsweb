#-*- coding: utf-8 -*-
import platform
import importlib
if platform.python_version().startswith('2.7.'):
    import sys
    importlib.reload(sys)
    sys.setdefaultencoding('utf8')