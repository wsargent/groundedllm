import re
from typing import List

from haystack import component
from haystack.dataclasses import ByteStream
from haystack_integrations.components.connectors.github import GitHubIssueViewer


@component
class GithubIssueResolver:
    """This class looks for github issues and directs them to GitHubIssueViewer"""

    def __init__(self):
        issue_pattern = r"https?://(?:(?:www|m)\.)?github\.com/([^/]+)/([^/]+)/issues/(\d+)(?:[/?#].*)?$"

        # Compile it for better performance if using multiple times
        self.issue_regex = re.compile(issue_pattern)

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        # https://docs.haystack.deepset.ai/reference/integrations-github#githubissueviewer
        viewer = GitHubIssueViewer()
        for url in urls:
            # Head document is the issue
            # Body documents are the comments
            viewer.run(url)["documents"]

        # XXX Need to turn these documents into a single bytestream
        return list()

    def can_handle(self, url: str) -> bool:
        return self.issue_regex.match(url) is not None
