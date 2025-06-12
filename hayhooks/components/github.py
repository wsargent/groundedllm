import re
from typing import List

from haystack import component
from haystack.dataclasses import ByteStream
from haystack.utils import Secret
from haystack_integrations.components.connectors.github import GitHubIssueViewer
from loguru import logger


@component
class GithubIssueContentResolver:
    """This class looks for github issues and directs them to GitHubIssueViewer"""

    def __init__(self, github_token: Secret = Secret.from_env_var("GITHUB_API_KEY"), raise_on_failure: bool = False):
        issue_pattern = r"https?://(?:(?:www|m)\.)?github\.com/([^/]+)/([^/]+)/issues/(\d+)(?:[/?#].*)?$"

        self.github_token = github_token
        self.raise_on_failure = raise_on_failure

        # Compile it for better performance if using multiple times
        self.issue_regex = re.compile(issue_pattern)

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        logger.debug(f"Using GithubIssueContentResolver for urls: {urls}")
        # https://docs.haystack.deepset.ai/reference/integrations-github#githubissueviewer
        viewer = GitHubIssueViewer(github_token=self.github_token, raise_on_failure=self.raise_on_failure, retry_attempts=2)
        streams = []
        for url in urls:
            # Head document is the issue
            # Body documents are the comments
            result = viewer.run(url)
            if "documents" in result:
                issue_and_comments = result["documents"]
                issue = issue_and_comments.head
                logger.debug(f"Using GithubIssueContentResolver: issue = {issue}")
                # XXX Need to turn these documents into a single bytestream, for now just ignore comments
                # comments = documents[1:]
                stream = ByteStream.from_string(text=issue.content, meta=issue.meta)
                streams.append(stream)
            else:
                logger.warning(f"Using GithubIssueContentResolver: no documents in {url}")

        return streams

    def can_handle(self, url: str) -> bool:
        return self.issue_regex.match(url) is not None
