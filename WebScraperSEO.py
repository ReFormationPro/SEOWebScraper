#!/usr/bin/env python
# -*- coding: utf-8 -*-
from ExternalsMapper import ExternalsMapper
from BacklinksQuery import BacklinksQuery
import os.path
from traceback import print_stack
from Utils import *

class WebScraperSEO():
    """
    domains: Initial domains to start scraping
    maxExternalLinkPerDomain: Limit for external links to be found by externals mapper per domain
    reportNoFollowLinks: If true, no follow links will be looked up with externals mapper too
    externalsCSVFileName: Name of the CSV file which has ExternalMapper results.
    backlinksCSVFileName: Name of the CSV file which has BacklinksQuery results.
    """
    DEFAULT_BACKLINKS_CSV_FILENAME = "backlinks.csv"
    DEFAULT_EXTERNALS_CSV_FILENAME = "externallinks.csv"
    def __init__(self, domains, maxExternalLinkPerDomain, reportNoFollowLinks, externalsCSVFileName=DEFAULT_EXTERNALS_CSV_FILENAME, backlinksCSVFileName=DEFAULT_BACKLINKS_CSV_FILENAME, proxies=[], tokens=[]):
        if os.path.isfile(externalsCSVFileName):
            input("WARNING: File '%s' already exists. It will be overwritten when you continue. Move it if you do not want to lose it."%externalsCSVFileName)
        if os.path.isfile(backlinksCSVFileName):
            input("WARNING: File '%s' already exists. It will be overwritten when you continue. Move it if you do not want to lose it."%backlinksCSVFileName)
        self.externalsMapper = ExternalsMapper([], maxExternalLinkPerDomain, externalsCSVFileName)
        self.backlinksQuery = BacklinksQuery(domains, reportNoFollowLinks, backlinksCSVFileName, proxies, tokens)
        self.backlinksQuery.setOnExternalSearchDomainFoundCallback(self.externalsMapper.onExternalSearchDomainFound)
        self.externalsMapper.setOnBacklinkSearchDomainFoundCallback(self.backlinksQuery.onBacklinkSearchDomainFound)
        self.externalsMapper.setErrorCallback(self.externalsMapperErrorCallback)
        self.backlinksQuery.setErrorCallback(self.backlinksQueryErrorCallback)

    def loadState(self, externalsFile, backlinksFile):
        """
        Loads states of scrapers. Can be used with recovery files.
        """
        self.externalsMapper.loadState(externalsFile)
        self.backlinksQuery.loadState(backlinksFile)

    def saveState(self, externalsFile, backlinksFile):
        """
        Saves states of scrapers.
        """
        self.externalsMapper.saveState(externalsFile)
        self.backlinksQuery.saveState(backlinksFile)

    def start(self):
        self.backlinksQuery.start()
        self.externalsMapper.start()

    def stop(self):
        self.backlinksQuery.stop()
        self.externalsMapper.stop()

    def join(self):
        try:
            self.backlinksQuery.join()
            self.externalsMapper.join()
        except KeyboardInterrupt:
            print("KeyboardInterrupt, saving state")
            print("WARNING: Do not loadState with existing csv file names. In that case they will be overwritten.")
            self.saveState("recovery_keyboardinterrupt.ext", "recovery_keyboardinterrupt.bac")

    def backlinksQueryErrorCallback(self, exception=""):
        self.stop()
        print()
        print("BacklinksQuery had to be stopped.")
        print("BacklinksQuery status is being saved to 'recovery.bac'")
        print("Externals Mapper status is being saved to 'recovery.ext'")
        print("Externals Mapper will run till its current unprocessed domains are processed then application will quit.")
        print("WARNING: Do not loadState with existing csv file names. In that case they will be overwritten.")
        self.saveState("recovery.ext", "recovery.bac")
        print("Details: ")
        print(exception)
        printException(exception)
        print()

    def externalsMapperErrorCallback(self, exception=""):
        self.stop()
        print()
        print("Externals Mapper had to be stopped.")
        print("Externals Mapper status is being saved to 'recovery.ext'")
        print("BacklinksQuery status is being saved to 'recovery.bac'")
        print("WARNING: Do not loadState with existing csv file names. In that case they will be overwritten.")
        self.saveState("recovery.ext", "recovery.bac")
        print("Details: ")
        print(exception)
        printException(exception)
        print()


