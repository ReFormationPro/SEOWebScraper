#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv

class Export:
    def __init__(self, fileName, headers):
        self.csvfile = open(fileName, 'w', newline='', encoding='utf-8')
        #self.writer = csv.writer(self.csvfile, delimiter=' ', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        if type(headers) == list:
        	self.dictwriter = csv.DictWriter(self.csvfile, headers)
        	self.dictwriter.writeheader()
        else:
        	# Headers are an object
        	self.dictwriter = csv.DictWriter(self.csvfile, headers.keys())
        	self.writerow(headers)

    def writerow(self, obj):
        self.dictwriter.writerow(obj)
        self.csvfile.flush()
    
    def close(self):
        if self.csvfile != None:
            self.csvfile.close()
            self.csvfile = None
    
    def __del__(self):
        self.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
