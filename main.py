#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from config import *
from WebScraperSEO import WebScraperSEO

def buildProxies(ipList, port, user, passw):
    return list(map(
        lambda ip: {'http': '%s://%s:%s@%s:%s'%("http",user,passw,ip,str(port)), 
        'https': '%s://%s:%s@%s:%s'%("https",user,passw,ip,str(port))}
        , ipList))

def main():
    global scraper
    """
    Scans for backlinks and external links in breadth first order.
    """
    if len(sys.argv) == 1:
        print("Usage: python3 %s initial_domain [max external link per domain=10] [reportNoFollowLinks=0]" % sys.argv[0])
        return
    initial_domain = sys.argv[1]
    maxExternalLinkPerDomain = 10
    reportNoFollowLinks = False
    if len(sys.argv) >= 3:
        try:
            maxExternalLinkPerDomain = int(sys.argv[2])
        except ValueError:
            print("Max External Link Per Domain must be an integer")
            return
    if len(sys.argv) >= 4:
        try:
            reportNoFollowLinks = bool(int(sys.argv[2]))
        except ValueError:
            print("reportNoFollowLinks must be an integer")
            return
    # For debugging purposes, you can add your own tokens like this.
    tokens = []
    # Proxy ips
    ipList = [""]
    proxies = buildProxies(ipList, 47685, "", "")
    proxies = []
    scraper = WebScraperSEO([initial_domain], maxExternalLinkPerDomain, reportNoFollowLinks, proxies=proxies, tokens=tokens)
    #scraper.loadState("recovery.ext", "recovery.bac")
    scraper.start()
    scraper.join()
    quit()

if __name__ == "__main__":
    main()
