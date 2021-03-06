# -*- coding: UTF-8 -*-

from __future__ import unicode_literals

try:
    from urlparse import urlparse, parse_qs
except ImportError:  # Python 3
    from urllib.parse import urlparse, parse_qs

from didel.base import DidelEntity, ROOT_URL
from didel.souputils import parse_homemade_dl
import re, os, datetime

from time import mktime
from os import mkdir

class CoursePage(DidelEntity):
    """
    A common base for Course-related pages
    """

    def __init__(self, ref):
        super(CoursePage, self).__init__()
        if ref.startswith('/'):
            self.path = ref
        else:
            self.path = self.URL_FMT.format(ref=ref)
        self.ref = ref



class CourseAssignment(CoursePage):
    """
    A course assignment
    """

    def __init__(self, path, course_code):
        super(CourseAssignment, self).__init__(path)
        self.course_code = course_code


    def populate(self, soup, session, **kw):
        content = soup.select('#courseRightContent')[0]
        attrs = parse_homemade_dl(content.select('p small')[0])
        self.title = attrs.get('titre')
        self.begin = attrs.get('du')
        self.end = attrs.get('au')
        self.submission_type = attrs.get('type de soumission')
        self.work_type = attrs.get('type de travail')
        self.visibility = attrs.get(u'visibilit\xe9 de la soumission')
        self.assig_id = parse_qs(urlparse(self.path).query)['assigId'][0]


    def submit(self, student, title, datafile, description=''):
        """
        Create a new submission for this assignment
        - ``student``: a ``Student`` object for the currently connected user
        - ``title``: the assignment's title
        - ``datafile``: an open file-like object for the attachment
        - ``description``: an optional description
        """
        authors = '%s %s' % (student.lastname, student.firstname)
        data = {
            'claroFormId': '42',
            'cmd': 'exSubWrk',
            'cidReset': 'true',
            'cidReq': self.course_code,
            'wrkTitle': title,
            'wrkAuthor': authors,
            'wrkTxt': description,
            'submitWrk': 'Ok',
        }
        files = {
            'wrkFile': datafile
        }
        path_fmt = '/claroline/work/user_work.php?assigId={aid}&authId={uid}'
        path = path_fmt.format(aid=self.assig_id, uid=student.auth_id)
        resp = self.session.post(path, data=data, files=files)
        return resp.ok and title in resp.text



class CourseAssignments(CoursePage, list):
    """
    Assignments list for a course
    """

    URL_FMT = '/claroline/work/work.php?cidReset=true&cidReq={ref}'

    def populate(self, soup, session):
        trs = soup.select('#courseRightContent table tbody tr')
        path_fmt = '/claroline/work/%s'
        for tr in trs:
            path = path_fmt % tr.select('a')[0].attrs['href']
            self.append(CourseAssignment(path, self.ref))



class Course(CoursePage):
    """
    A course. It has the following attributes: ``title``, ``teacher``,
    ``about`` and the following sub-resources:
        - ``assignments``

    Additionally, it keeps a reference to its student with ``student``
    """

    URL_FMT = '/claroline/course/index.php?cid={ref}&cidReset=true&cidReq={ref}'

    def __init__(self, ref, student=None):
        """
        Create a new course from a reference, and an optional student
        """
        super(Course, self).__init__(ref)
        self.student = student
        self.add_resource('assignments', CourseAssignments(ref))


    def populate(self, soup, session):
        header = soup.select('.courseInfos')[0]
        self.title = header.select('h2 a')[0].get_text()
        self.teacher = header.select('p')[0].get_text().split('\n')[-1].strip()
        about = soup.select('#portletAbout')
        if about:
            self.about = about[0].get_text().strip()


    def docs_and_links(self, path):
        """
        synchronize didel documents with user
        """
        if not (os.path.isdir(path)):
            raise IOError # if the path defined in SOURCE_FILE (cf config.py) isn't available
        d = DocumentsLinks(self.ref)
        d.fetch(self.session)
        d.synchronize(path)


    def enroll(self, key=None):
        """
        Enroll the current student in this course. Some courses require a key
        to enroll, give it as ``key``.
        """
        path = '/claroline/auth/courses.php'
        ok_text = u'Vous êtes désormais inscrit'
        params = {'cmd': 'exReg', 'course': self.ref}
        if not key:
            return self.session.get_ensure_text(path, ok_text, params=params)
        data = params.copy()
        data['registrationKey'] = 'scade'
        resp = self.session.post(path, params=params, data=data)
        return resp.ok and ok_text in resp.text


    def unenroll(self):
        """
        Unenroll the current student from this course.
        """
        path = '/claroline/auth/courses.php'
        text = u'Vous avez été désinscrit'
        params = {'cmd': 'exUnreg', 'course': self.ref}
        return self.session.get_ensure_text(path, text, params=params)


class DocumentsLinks(DidelEntity):

    URL_FMT = '/claroline/document/document.php?cidReset=true&cidReq={ref}'

    def __init__(self, ref, path=None):
        super(DocumentsLinks, self).__init__()
        self.ressources = {}
        self.ref = ref
        if path :
            self.path = path
            self.ref = ""            
        else:
            self.path = self.URL_FMT.format(ref=ref)


    def populate(self, soup, session):
        """
        Get all documents and folder of a course.
        """
        table = soup.select(".claroTable tbody tr[align=center]")
        for line in table:
            cols = line.select("td")
            item = cols[0].select(".item")[0]
            name = item.contents[1].strip()
            date = cols[2].select("small")[0].contents[0].strip()
            url = cols[0].select("a")[0].attrs["href"].strip()
            if(re.match(r"^<img (alt=\"\")? src=\"/web/img/folder", str(item.select("img")[0]))) is not None:
                doc = DocumentsLinks("", url)
                doc.fetch(self.session)
                self.add_resource(name, doc)
            else:
                self.add_resource(name, Document(name, url, date))

    def timestamp(self, date):
        return mktime(datetime.datetime.strptime(date, "%d.%m.%Y").timetuple())

 
    def synchronize(self, path):
        """
        compare files on didel with file in folder,
            and calling download add or reset files'user
            only if not exist or older
        """
        path = "%s/%s" % (path, self.ref)
        if not os.path.isdir(path):
            mkdir(path)
        for k in self._resources:
            if(isinstance(self._resources[k], DocumentsLinks)): 
                self._resources[k].synchronize("%s/%s" % (path, k))
            else:
                no_file = not os.path.exists("%s/%s" % (path, k))
                didel_file = self.timestamp(self._resources[k].date)
                if no_file or (didel_file > os.stat("%s/%s" % (path, k)).st_mtime):
                    self.download(self._resources[k], path)
    

    def download(self, document, path):
        response = self.session.get(ROOT_URL + document.url)
        document.path = "%s/%s" % (path, document.name)
        with open(document.path, 'w') as file:
            file.write(response.content)
        


class Document(object):

    def __init__(self, name, url, date):
        self.name = name
        self.url = url
        self.date = date

