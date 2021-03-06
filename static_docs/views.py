# -*- coding: utf-8 -*-
# LICENCE: This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.http import Http404
from django.views.generic.base import TemplateView
from geany.decorators import cache_function, CACHE_TIMEOUT_24HOURS
from static_docs.github_client import GitHubApiClient
import logging
import re


RELEASE_REGEXP = re.compile(r'^Geany (?P<version>[0-9\.]+) \((?P<date>.*)\)$')
DATE_PATTERNS_TO_BE_IGNORED = (u'TBD', u'TBA', u'unreleased')

logger = logging.getLogger(__name__)


########################################################################
class ReleaseDto(object):
    """Simple data holder"""

    #----------------------------------------------------------------------
    def __init__(self):
        self.version = None
        self.release_date = None
        self.release_notes = None

    #----------------------------------------------------------------------
    def __repr__(self):
        return u'Geany %s (%s)' % (self.version, self.release_date)


########################################################################
class StaticDocsView(TemplateView):
    """"""

    #----------------------------------------------------------------------
    def __init__(self, *args, **kwargs):
        super(StaticDocsView, self).__init__(*args, **kwargs)
        self._file_contents = None

    #----------------------------------------------------------------------
    def _fetch_file_via_github_api(self, filename):
        client = GitHubApiClient()
        self._file_contents = client.get_file_contents(filename)


########################################################################
class ReleaseNotesView(StaticDocsView):
    """
    Grab the NEWS file from GIT master via Github API, parse it and send it back to the template
    """

    template_name = "pages/documentation/releasenotes.html"

    #----------------------------------------------------------------------
    def get_context_data(self, version=None, **kwargs):
        releases = self._get_release_notes()
        release = None

        if version is not None:
            # search for the requested release in the list (we could index the list into a
            # dictionary but we need the index only at this point)
            for rel in releases:
                if rel.version == version:
                    release = rel
                    break
            else:
                raise Http404()
        else:
            # use the first element in the list which is the latest
            release = releases[0]

        context = super(ReleaseNotesView, self).get_context_data(**kwargs)
        context['selected_release'] = release
        context['releases'] = releases
        return context

    #----------------------------------------------------------------------
    @cache_function(CACHE_TIMEOUT_24HOURS)
    def _get_release_notes(self):
        self._fetch_file_via_github_api('NEWS')
        return self._parse_news_file()

    #----------------------------------------------------------------------
    def _parse_news_file(self):
        releases = list()
        current_release = None
        current_release_notes = None
        for line in self._file_contents.splitlines():
            if line.startswith(u'Geany'):
                version, date = self._parse_release_line(line)
                if not version or date in DATE_PATTERNS_TO_BE_IGNORED:
                    # mark for later exclusion
                    version, date = (None, None)
                # if we have a previous release already processed,
                # compress the list of lines to a string
                if current_release is not None:
                    current_release.release_notes = u'\n'.join(current_release_notes)
                # make a new release
                current_release = ReleaseDto()
                current_release.version = version
                current_release.release_date = date
                releases.append(current_release)
                current_release_notes = list()
            else:
                current_release_notes.append(line)

        # filter out releases to ignore
        releases = [release for release in releases if release.version is not None]
        return releases

    #----------------------------------------------------------------------
    def _parse_release_line(self, line):
        match = RELEASE_REGEXP.match(line)
        if match:
            return match.group('version'), match.group('date')
        else:
            logger.warn(u'Failed parsing NEWS file: release line "%s" invalid', line)
        return None, None


########################################################################
class ToDoView(StaticDocsView):
    """
    Grab the TODO file from GIT master via Github API, parse it and send it back to the template
    """

    template_name = "pages/documentation/todo.html"

    #----------------------------------------------------------------------
    def get_context_data(self, **kwargs):
        todo = self._get_todo()
        context = super(ToDoView, self).get_context_data(**kwargs)
        context['todo'] = todo
        return context

    #----------------------------------------------------------------------
    @cache_function(CACHE_TIMEOUT_24HOURS)
    def _get_todo(self):
        self._fetch_file_via_github_api('TODO')
        return self._parse_news_file()

    #----------------------------------------------------------------------
    def _parse_news_file(self):
        return self._file_contents
