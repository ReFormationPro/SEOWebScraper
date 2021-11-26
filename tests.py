#!/usr/bin/env python
# -*- coding: utf-8 -*-

from Export import Export
from ExternalsMapper import ExternalsMapper

def test_exporter():
	HEADERS = {"of_domain": "of_domain", "url_from": "url_from", "url_to": "url_to", "title": "title", "anchor": "anchor", "nofollow": "nofollow", "inlink_rank": "page_rank", "domain_inlink_rank": "domain_rank", "first_seen": "first_seen", "last_visited": "last_visited"}
	FIELDNAMES = ["of_domain", "url_from", "url_to", "title", "anchor", 'nofollow', 'inlink_rank', 'domain_inlink_rank', 'first_seen', 'last_visited']

	obj1 = {"of_domain": "1", "url_from": "2", "url_to": "3", "title": "title", "anchor": "anchor", "nofollow": "nofollow", "inlink_rank": "page_rank", "domain_inlink_rank": "domain_rank", "first_seen": "first_seen", "last_visited": "last_visited"}
	obj2 = {"of_domain": "12", "url_from": "23", "url_to": "3", "title": "title", "anchor": "anchor", "nofollow": "nofollow", "inlink_rank": "page_rank", "domain_inlink_rank": "domain_rank", "first_seen": "first_seen", "last_visited": "last_visited"}

	e = Export("test.csv", HEADERS)
	e2 = Export("test2.csv", FIELDNAMES)

	e.writerow(obj1)
	e.writerow(obj2)
	e2.writerow(obj1)
	e2.writerow(obj2)
	e.close()
	e2.close()
	

def testExternalsMapper(url=[""]):
    externalsMapper = ExternalsMapper(url, 10, "test.csv")
    externalsMapper.start()


