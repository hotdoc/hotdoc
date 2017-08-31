# -*- coding: utf-8 -*-
#
# Copyright © 2015,2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2015,2016 Collabora Ltd
#
# This library is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

# pylint: disable=missing-docstring

import re
import os
import shutil
import json
import glob
import threading
import multiprocessing

from concurrent import futures
from collections import defaultdict, namedtuple, OrderedDict

import lxml.html

from hotdoc.core.exceptions import InvalidOutputException
from hotdoc.utils.loggable import info as core_info, Logger

from hotdoc.extensions.search.trie import Trie


ContextualizedURL = namedtuple('ContextualizedURL', ['url', 'context'])


def info(message):
    core_info(message, domain='search-extension')

Logger.register_warning_code('invalid-html', InvalidOutputException,
                             'search-extension')

SECTIONS_SELECTOR = (
    './div[@id]'
)

INITIAL_SELECTOR = (
    './/div[@id="main"]'
)

TITLE_SELECTOR = (
    './/*[self::h1 or self::h2 or self::h3 or '
    'self::h4 or self::h5 or self::h6]'
)

TOK_REGEX = re.compile(r'[a-zA-Z_][a-zA-Z0-9_\.]*[a-zA-Z0-9_]*')


def get_sections(root, selector='./div[@id]'):
    return root.xpath(selector)


def parse_content(section, stop_words, selector='.//p'):
    for elem in section.xpath(selector):
        context = {'gi-language': 'default'}
        text = lxml.html.tostring(elem, method="text",
                                  encoding='unicode')

        id_ = None
        while id_ is None and elem is not None:
            if context['gi-language'] == 'default':
                klasses = elem.attrib.get('class', '').split(' ')
                try:
                    klasses.remove('gi-symbol')
                    context['gi-language'] = klasses[0].split('-')[2]
                except ValueError:
                    pass

            id_ = elem.attrib.get('id')
            elem = elem.getparent()

        tokens = TOK_REGEX.findall(text)

        for token in tokens:
            original_token = token + ' '
            if token.lower() in stop_words:
                yield (None, original_token, id_, context)
                continue
            if token.endswith('.'):
                yield (token.rstrip('.'), original_token, id_, context)
                continue

            yield (token, original_token, id_, context)

        yield (None, '\n', id_, context)


def write_fragment(fragments_dir, url, text):
    dest = os.path.join(fragments_dir, url + '.fragment')
    dest = dest.replace('#', '-')
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    _ = open(dest, 'w')

    _.write("fragment_downloaded_cb(")
    _.write(json.dumps({"url": url, "fragment": text}))
    _.write(");")
    _.close()


# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
def parse_file(root_dir, root, filename, stop_words, fragments_dir):
    if root.attrib.get('id') == 'main':
        initial = root
    else:
        initial = root.xpath(INITIAL_SELECTOR)

        if not len(initial):
            return

        initial = initial[0]

    url = os.path.relpath(filename, root_dir)

    sections = get_sections(initial, SECTIONS_SELECTOR)
    for section in sections:
        section_url = '%s#%s' % (url, section.attrib.get('id', '').strip())
        subsections = defaultdict(str)

        for tok, text, id_, context in parse_content(section, stop_words,
                                                     selector=TITLE_SELECTOR):
            if id_:
                section_id = '%s#%s' % (url, id_)
            else:
                section_id = section_url

            subsections[section_id] += text

            if tok is None:
                continue

            yield tok, section_id, True, context
            if any(c.isupper() for c in tok):
                yield tok.lower(), section_id, True, context

        for tok, text, id_, context in parse_content(section, stop_words):
            if id_:
                section_id = '%s#%s' % (url, id_)
            else:
                section_id = section_url

            subsections[section_id] += text

            if tok is None:
                continue

            yield tok, section_id, False, context
            if any(c.isupper() for c in tok):
                yield tok.lower(), section_id, False, context

        for section_id, section_text in subsections.items():
            write_fragment(fragments_dir,
                           section_id,
                           section_text)


def prepare_folder(dest):
    if os.path.isdir(dest):
        return

    try:
        shutil.rmtree(dest)
    except OSError:
        pass

    try:
        os.mkdir(dest)
    except OSError:
        pass


# pylint: disable=too-many-instance-attributes
class SearchIndex(object):

    def __init__(self, scan_dir, output_dir, private_dir):
        self.__scan_dir = scan_dir
        self.__output_dir = output_dir
        self.__private_dir = private_dir

        prepare_folder(self.__search_dir)
        prepare_folder(self.__fragments_dir)

        self.__indices_lock = threading.Lock()
        self.__full_index = defaultdict(list)
        self.__new_index = defaultdict(list)
        self.__trie = Trie()

        self.__filler = futures.ThreadPoolExecutor(
            max_workers=multiprocessing.cpu_count() * 5)
        here = os.path.dirname(__file__)
        with open(os.path.join(here, 'stopwords.txt'), 'r') as _:
            self.__stop_words = set(_.read().split())

        self.__futures = []
        self.__connected_all_projects = False

    def process(self, path, lxml_tree):
        self.__futures.append(self.__filler.submit(self.fill, path, lxml_tree))

    def write(self):
        for future in self.__futures:
            # Make sure all the filling is done.
            future.result()
        self.save()

    @property
    def __search_dir(self):
        return os.path.join(self.__output_dir, 'search')

    @property
    def __fragments_dir(self):
        return os.path.join(self.__search_dir, 'hotdoc_fragments')

    def __get_fragments(self, filenames):
        fragments = set()

        for filename in filenames:
            url = os.path.relpath(filename, self.__scan_dir)
            for fragment in glob.glob(
                    os.path.join(self.__fragments_dir, url) + '*'):
                fragments.add(os.path.relpath(fragment,
                                              self.__fragments_dir)[:-9])
                os.unlink(fragment)

        return fragments

    def fill(self, filename, lxml_tree):
        for token, section_url, prioritize, context in parse_file(
                self.__scan_dir,
                lxml_tree,
                filename,
                self.__stop_words,
                self.__fragments_dir):

            self.__indices_lock.acquire()
            contextualized_url = ContextualizedURL(section_url, context)
            if not prioritize:
                self.__full_index[token].append(contextualized_url)
                self.__new_index[token].append(contextualized_url)
            else:
                self.__full_index[token].insert(0, contextualized_url)
                self.__new_index[token].insert(0, contextualized_url)
            self.__indices_lock.release()

    def save(self):
        self.__indices_lock.acquire()
        for key, value in sorted(self.__new_index.items()):
            self.__trie.insert(key)

            deduped = OrderedDict()
            for url in value:
                try:
                    context = deduped[url.url]
                    for key_, val_ in url.context.items():
                        try:
                            vset = context[key_]
                            vset.add(val_)
                        except KeyError:
                            context[key_] = set([val_])
                except KeyError:
                    deduped[url.url] = \
                        {k: set([v]) for k, v in url.context.items()}

            urls = []
            for url, context in deduped.items():
                for key_, val_ in context.items():
                    context[key_] = list(val_)
                urls.append({'url': url, 'context': context})

            metadata = {'token': key, 'urls': urls}

            with open(os.path.join(self.__search_dir, key), 'w') as _:
                _.write('urls_downloaded_cb(%s);' % json.dumps(metadata))

        self.__trie.to_file(os.path.join(self.__private_dir, 'search.trie'),
                            os.path.join(self.__output_dir, 'trie_index.js'))

        self.__indices_lock.release()
