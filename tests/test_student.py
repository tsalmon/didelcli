# -*- coding: UTF-8 -*-

import platform

if platform.python_version() < '2.7':
    import unittest2 as unittest
else:
    import unittest

from os import remove
from tempfile import NamedTemporaryFile

import requests
import responses

from didel.student import Student

class TestSession(unittest.TestCase):

	def test_explore_docs_n_liens(self):
		student = Student("", "")
		course = student.get_course("M2T3STAGES")	
		print "%s - %s" % (course.title, course.teacher)
		course.docs_and_links("/Users/salmon/Documents/python/test_didelcli_folder")
