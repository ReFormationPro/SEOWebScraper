from functools import *

class DomainData:
    domain = ""
    backlinks = []
    externals = []
    def __init__(self, domain, backlinks, externals):
        self.domain = domain
        self.backlinks = backlinks
        self.externals = externals

    def __hash__(self):
        """
        Sum of ord values of chars of domain string
        """
        return reduce(lambda x, y: x+ord(y), self.domain, 0)
    
    def __str__(self):
        return """DomainData("%s", %s, %s)""" %(self.domain, self.backlinks, self.externals)

    def __repr__(self):
        return self.__str__()


