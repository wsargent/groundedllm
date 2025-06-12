import re
from typing import Dict, List, Optional

from haystack import component
from haystack.components.builders.prompt_builder import PromptBuilder
from haystack.dataclasses import ByteStream
from haystack.utils import Secret
from haystack_integrations.components.connectors.github import GitHubIssueViewer
from loguru import logger

from resources.utils import read_resource_file


@component
class GithubIssueContentResolver:
    """This class looks for github issues and directs them to GitHubIssueViewer"""

    def __init__(self, github_token: Optional[Secret] = None, raise_on_failure: bool = False):
        issue_pattern = r"https?://(?:(?:www|m)\.)?github\.com/([^/]+)/([^/]+)/issues/(\d+)(?:[/?#].*)?$"

        self.github_token = github_token
        self.raise_on_failure = raise_on_failure

        # Compile it for better performance if using multiple times
        self.issue_regex = re.compile(issue_pattern)

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]) -> Dict[str, list[ByteStream]]:
        logger.debug(f"Using GithubIssueContentResolver for urls: {urls}")
        # https://docs.haystack.deepset.ai/docs/githubissueviewer
        # https://docs.haystack.deepset.ai/reference/integrations-github#githubissueviewer
        streams: List[ByteStream] = []
        try:
            viewer = GitHubIssueViewer(github_token=self.github_token, raise_on_failure=self.raise_on_failure, retry_attempts=2)
            template = read_resource_file("github_issue_prompt.md")
            prompt_builder = PromptBuilder(template=template, required_variables=["documents"])

            for url in urls:
                # Head document is the issue
                # Body documents are the comments
                result = viewer.run(url)
                logger.debug(f"GitHubIssueViewer result: {result}")
                if "documents" in result:
                    documents = result["documents"]
                    issue = documents[0]
                    logger.debug(f"GitHubIssueViewer issue: {issue}")
                    results = prompt_builder.run(documents=documents)
                    contents = results.get("prompt")
                    if contents:
                        stream = ByteStream.from_string(text=contents, meta=issue.meta, mime_type="text/markdown")
                        streams.append(stream)
                    else:
                        logger.error(f"No content found in prompt for url: {url}")
                else:
                    logger.warning(f"Using GithubIssueContentResolver: no documents in {url}")

            logger.debug(f"GithubIssueContentResolver streams: {streams}")
            return {"streams": streams}
        except Exception as e:
            logger.warning(f"Failed to fetch {urls} using Github: {str(e)}")
            if self.raise_on_failure:
                raise e
            else:
                logger.debug(f"GithubIssueContentResolver error streams: {streams}")
                return {"streams": streams}

    def can_handle(self, url: str) -> bool:
        return self.issue_regex.match(url) is not None
