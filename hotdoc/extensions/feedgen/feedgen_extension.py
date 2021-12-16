import os
import urllib.parse

from hotdoc.core.extension import Extension
from hotdoc.core.tree import Page
from hotdoc.core.formatter import Formatter
from schema import And, Use, Optional
from feedgen.feed import FeedGenerator
from datetime import date, datetime, timezone

PNAME = 'feedgen'
HERE = os.path.abspath(os.path.dirname(__file__))

Page.meta_schema[Optional('add-to-feedgen')] = And(bool)
Page.meta_schema[Optional('feedgen-published')] = And(date)
Page.meta_schema[Optional('feedgen-updated')] = And(date)


class FeedgenExtension(Extension):
    extension_name = PNAME
    argument_prefix = PNAME

    activated = False
    __connected = False
    __base_url = None
    __feed = FeedGenerator()

    def __init__(self, app, project):
        self.__repo = None
        Extension.__init__(self, app, project)

    @staticmethod
    def add_arguments(parser):
        group = parser.add_argument_group(
            'Generate Atom feed',
            'Allow generating a feed.xml, in Atom format')

        group.add_argument(
            '--feedgen-activate',
            action="store_true",
            help="Activate the feedgen extension",
            dest='feedgen_activate')

        group.add_argument(
            '--feedgen-base-url',
            help="Base URL for links",
            dest='feedgen_base_url')

    def parse_toplevel_config(self, config):
        super().parse_toplevel_config(config)
        FeedgenExtension.activated = bool(
            config.get('feedgen_activate', False))
        FeedgenExtension.base_url = config.get('feedgen_base_url')

    def __writing_page_cb(self, formatter, page, path, lxml_tree):
        if not page.meta.get('add-to-feedgen', True):
            return

        published_date = page.meta.get('feedgen-published')
        updated_date = page.meta.get('feedgen-updated', published_date)

        if published_date is not None:
            published = datetime.combine(
                published_date, datetime.min.time(), tzinfo=timezone.utc)
        else:
            published = None

        if updated_date is not None:
            updated = datetime.combine(
                updated_date, datetime.min.time(), tzinfo=timezone.utc)
        else:
            updated = None

        entry = FeedgenExtension.__feed.add_entry()

        if FeedgenExtension.base_url is not None:
            href = urllib.parse.urljoin(
                FeedgenExtension.base_url, page.link.ref)
        else:
            href = page.link.ref

        entry.id(href)
        entry.title(page.link.title)
        entry.link(href=href, type='text/html', title=page.link.title)
        entry.published(published)
        entry.updated(updated)

        if page.short_description:
            entry.summary(page.short_description)

        entry.content(page.formatted_contents, type='html')

    def __project_written_out_cb(self, project):
        html_dir = os.path.join(self.app.output, 'html')

        FeedgenExtension.__feed.id(
            FeedgenExtension.base_url or project.project_name)
        FeedgenExtension.__feed.title(project.project_name)

        if FeedgenExtension.base_url is not None:
            FeedgenExtension.__feed.link(
                href=FeedgenExtension.base_url,
                type='text/html')
            FeedgenExtension.__feed.link(
                href=urllib.parse.urljoin(
                    FeedgenExtension.base_url, 'feed.xml'),
                rel='self',
                type='application/atom+xml')

        FeedgenExtension.__feed.atom_file(
            os.path.join(html_dir, 'feed.xml'), pretty=True)

    def setup(self):
        super(FeedgenExtension, self).setup()
        if not FeedgenExtension.activated:
            return

        for ext in self.project.extensions.values():
            ext.formatter.writing_page_signal.connect(self.__writing_page_cb)

        if FeedgenExtension.__connected:
            return

        self.project.written_out_signal.connect_after(
            self.__project_written_out_cb)

        FeedgenExtension.__connected = True
