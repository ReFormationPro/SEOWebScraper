#!/usr/bin/env python
# -*- coding: utf-8 -*-
import traceback

def printException(ex):
    traceback.print_exception(type(ex), ex, ex.__traceback__)


