import mimetypes
import re
from typing import Dict, List, Optional

from haystack import component
from haystack.components.builders.prompt_builder import PromptBuilder
from haystack.dataclasses import ByteStream
from haystack.utils import Secret
from haystack_integrations.components.connectors.github import GitHubIssueViewer, GitHubRepoViewer
from loguru import logger

from resources.utils import read_resource_file

raw_url1 = "https://raw.githubusercontent.com/wsargent/jmxmvc/refs/heads/master/README.md"
raw_url2 = "http://raw.githubusercontent.com/octocat/Spoon-Knife/main/README.md"
raw_url3 = "https://raw.githubusercontent.com/torvalds/linux/master/Documentation/admin-guide/devices.rst"


@component
class GithubIssueContentResolver:
    """This class looks for github issues and directs them to GitHubIssueViewer"""

    def __init__(self, github_token: Optional[Secret] = None, raise_on_failure: bool = False):
        issue_pattern = r"https?://(?:(?:www|m)\.)?github\.com/([^/]+)/([^/]+)/issues/(\d+)(?:[/?#].*)?$"

        self.github_token = github_token
        self.raise_on_failure = raise_on_failure

        # Compile it for better performance if using multiple times
        self.issue_regex = re.compile(issue_pattern)
        self.raw_github_content_regex = re.compile(r"^(?:https?:\/\/)?raw\.githubusercontent\.com\/([a-zA-Z0-9_-]+)\/([a-zA-Z0-9_-]+)\/([a-zA-Z0-9._\/-]+)\/(.*)$")

    def parse_raw_github_url(self, url):
        match = self.raw_github_content_regex.match(url)
        if match:
            owner = match.group(1)
            repo = match.group(2)
            branch_or_commit = match.group(3)
            path = match.group(4)
            return {
                "owner": owner,
                "repository": repo,
                "branch_or_commit": branch_or_commit,
                "path": path,
            }
        return None

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


@component
class GithubRepoContentResolver:
    """This class looks for files and directories in a github repository and sends them to GitHubRepoViewer"""

    def __init__(self, github_token: Optional[Secret] = None, raise_on_failure: bool = False):
        # This matches every github repo file.
        repo_pattern = r"^(?:https?:\/\/)?github\.com\/([a-zA-Z0-9_-]+)\/([a-zA-Z0-9_-]+)(?:\/(?:blob|tree|raw|commit)\/([a-zA-Z0-9._-]+)\/(.*))?$"

        self.github_token = github_token
        self.raise_on_failure = raise_on_failure
        self.github_regex = re.compile(repo_pattern)

    def _parse_github_url(self, url):
        match = self.github_regex.match(url)
        if match:
            owner = match.group(1)
            repo = match.group(2)
            branch_or_commit = match.group(3)
            path = match.group(4)
            return {
                "owner": owner,
                "repository": repo,
                "branch_or_commit": branch_or_commit if branch_or_commit else None,
                "path": path if path else None,
            }
        return None

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]) -> Dict[str, list[ByteStream]]:
        logger.debug(f"Using GithubIssueContentResolver for urls: {urls}")
        # https://docs.haystack.deepset.ai/docs/githubissueviewer
        # https://docs.haystack.deepset.ai/reference/integrations-github#githubissueviewer
        streams: List[ByteStream] = []
        try:
            viewer = GitHubRepoViewer(github_token=self.github_token, raise_on_failure=self.raise_on_failure)

            for url in urls:
                github_dict = self._parse_github_url(url)
                logger.debug(f"GithubRepoContentResolver github_dict: {github_dict}")

                repo = github_dict["repository"]
                branch_or_commit = github_dict["branch_or_commit"]
                owner = github_dict["owner"]
                path = github_dict["path"]

                result = viewer.run(path=path, repo=f"{owner}/{repo}", branch=branch_or_commit)
                logger.debug(f"GithubRepoContentResolver result: {result}")
                if "documents" in result:
                    documents = result["documents"]
                    if documents:
                        for document in documents:
                            # can we guess the mime type from the file suffix?
                            path = document.meta.get("path")
                            # deprecated in 3.13 but we're on 3.12 here...
                            mime_type = mimetypes.guess_type(path, strict=False)[0]
                            logger.debug(f"GithubRepoContentResolver mime type for path {path} is {mime_type}")
                            stream = ByteStream.from_string(text=document.content, meta=document.meta, mime_type=mime_type)
                            streams.append(stream)
                    else:
                        logger.error(f"No documents for url: {url}")
                else:
                    logger.warning(f"Using GithubRepoContentResolver: no documents in {url}")

            logger.debug(f"GithubRepoContentResolver streams: {streams}")
            return {"streams": streams}
        except Exception as e:
            logger.warning(f"Failed to fetch {urls} using Github: {str(e)}")
            if self.raise_on_failure:
                raise e
            else:
                logger.debug(f"GithubRepoContentResolver error streams: {streams}")
                return {"streams": streams}

    def can_handle(self, url: str) -> bool:
        return self.github_regex.match(url) is not None
