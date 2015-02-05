# -*- coding: UTF-8 -*-

import platform

if platform.python_version() < '2.7':
    import unittest2 as unittest
else:
    import unittest

from didel.student import Student
from didel.cli import DidelCli

class TestStudent(unittest.TestCase):
	"""
	def test_explore_docs_n_liens(self):
		student = Student("", "")
		course = student.get_course("M2ASI")	
		print "%s - %s" % (course.title, course.teacher)
		course.docs_and_links("/Users/salmon/Documents/python/test_didelcli_folder")
	"""
	
	"""
	def test_pull_save(self):
		c = DidelCli(["didelcli", "pull:save", "path/to/didelpath"])
		c.run()
	"""
