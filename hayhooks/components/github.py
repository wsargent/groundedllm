import re
from typing import Dict, List, Optional

import httpx
from haystack import Document, component
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
        # This matches raw.githubusercontent.com URLs
        raw_pattern = r"^(?:https?:\/\/)?raw\.githubusercontent\.com\/([a-zA-Z0-9_-]+)\/([a-zA-Z0-9_-]+)\/(.+)$"
        # This matches GitHub pull request URLs
        pr_pattern = r"^(?:https?:\/\/)?github\.com\/([a-zA-Z0-9_-]+)\/([a-zA-Z0-9_-]+)\/pull\/(\d+)(?:[/?#].*)?$"

        self.github_token = github_token
        self.raise_on_failure = raise_on_failure
        self.github_regex = re.compile(repo_pattern)
        self.raw_github_regex = re.compile(raw_pattern)
        self.pr_regex = re.compile(pr_pattern)

    def _parse_github_url(self, url):
        # Try regular GitHub URL first
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

        # Try raw GitHub URL
        raw_match = self.raw_github_regex.match(url)
        if raw_match:
            owner = raw_match.group(1)
            repo = raw_match.group(2)
            remaining_path = raw_match.group(3)

            # Split the remaining path to extract branch and file path
            path_parts = remaining_path.split("/")

            # Handle complex branch names like refs/heads/master
            if len(path_parts) >= 3 and path_parts[0] == "refs":
                # For refs/heads/master, take first 3 parts as branch
                branch_or_commit = "/".join(path_parts[:3])
                path = "/".join(path_parts[3:])
            else:
                # For simple branch names, take first part as branch
                branch_or_commit = path_parts[0]
                path = "/".join(path_parts[1:]) if len(path_parts) > 1 else ""

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
            viewer = GitHubRepoViewer(github_token=self.github_token, raise_on_failure=self.raise_on_failure)

            for url in urls:
                github_dict = self._parse_github_url(url)
                logger.debug(f"GithubRepoContentResolver github_dict: {github_dict}")

                repo = github_dict["repository"]
                branch_or_commit = github_dict["branch_or_commit"]
                owner = github_dict["owner"]
                path = github_dict["path"]

                result = viewer.run(path=path or "", repo=f"{owner}/{repo}", branch=branch_or_commit)
                logger.debug(f"GithubRepoContentResolver result: {result}")
                if "documents" in result:
                    documents = result["documents"]
                    if documents:
                        for document in documents:
                            # can we guess the mime type from the file suffix?
                            path = document.meta.get("path")
                            # deprecated in 3.13 but we're on 3.12 here...
                            # mime_type = mimetypes.guess_type(path, strict=False)[0]
                            # If we have a document like a jekyll post that combines YAML and Markdown
                            # then the markdown convert can result in a completely empty document :-/
                            mime_type = "text/plain"
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
        return self.github_regex.match(url) is not None or self.raw_github_regex.match(url) is not None


@component
class GithubPRContentResolver:
    """This class looks for GitHub pull requests and directs them to GitHubPRViewer"""

    def __init__(self, github_token: Optional[Secret] = None, raise_on_failure: bool = False):
        pr_pattern = r"https?://(?:(?:www|m)\.)?github\.com/([^/]+)/([^/]+)/pull/(\d+)(?:[/?#].*)?$"

        self.github_token = github_token
        self.raise_on_failure = raise_on_failure
        self.pr_regex = re.compile(pr_pattern)

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]) -> Dict[str, list[ByteStream]]:
        logger.debug(f"Using GithubPRContentResolver for urls: {urls}")
        streams: List[ByteStream] = []
        try:
            viewer = GitHubPRViewer(github_token=self.github_token, raise_on_failure=self.raise_on_failure)

            for url in urls:
                result = viewer.run(url)
                logger.debug(f"GitHubPRViewer result: {result}")
                if "documents" in result:
                    documents = result["documents"]
                    if documents:
                        for document in documents:
                            # PR content is markdown by default
                            content = document.content or ""
                            stream = ByteStream.from_string(text=content, meta=document.meta, mime_type="text/markdown")
                            streams.append(stream)
                    else:
                        logger.error(f"No documents for url: {url}")
                else:
                    logger.warning(f"Using GithubPRContentResolver: no documents in {url}")

            logger.debug(f"GithubPRContentResolver streams: {streams}")
            return {"streams": streams}
        except Exception as e:
            logger.warning(f"Failed to fetch {urls} using GitHub PR: {str(e)}")
            if self.raise_on_failure:
                raise e
            else:
                logger.debug(f"GithubPRContentResolver error streams: {streams}")
                return {"streams": streams}

    def can_handle(self, url: str) -> bool:
        return self.pr_regex.match(url) is not None


@component
class GitHubPRViewer:
    """
    Fetches and parses GitHub pull requests into Haystack documents.

    The component takes a GitHub pull request URL and returns a list of documents where:
    - First document contains the main pull request content (title, description, metadata)
    - Additional documents can contain PR review comments if needed

    ### Usage example
    ```python
    viewer = GitHubPRViewer()
    docs = viewer.run(
        url="https://github.com/owner/repo/pull/123"
    )["documents"]
    ```
    """

    def __init__(self, github_token: Optional[Secret] = None, raise_on_failure: bool = False):
        """Initialize GitHubPRViewer.

        Args:
            github_token (Optional[Secret]): GitHub token for API access
            raise_on_failure (bool): Whether to raise an exception on failure
        """
        self.github_token = github_token
        self.raise_on_failure = raise_on_failure
        self.pr_regex = re.compile(r"https?://(?:(?:www|m)\.)?github\.com/([^/]+)/([^/]+)/pull/(\d+)(?:[/?#].*)?$")

    def _parse_pr_url(self, url: str) -> Optional[Dict[str, str]]:
        """Parse a GitHub PR URL to extract owner, repo, and PR number."""
        match = self.pr_regex.match(url)
        if match:
            return {
                "owner": match.group(1),
                "repo": match.group(2),
                "pr_number": match.group(3),
            }
        return None

    def _fetch_pr_data(self, owner: str, repo: str, pr_number: str) -> Optional[Dict]:
        """Fetch pull request data from GitHub API."""
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if self.github_token:
            token = self.github_token.resolve_value()
            headers["Authorization"] = f"Bearer {token}"

        try:
            with httpx.Client() as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch PR data for {owner}/{repo}/pull/{pr_number}: {str(e)}")
            if self.raise_on_failure:
                raise e
            return None

    @component.output_types(documents=List[Document])
    def run(self, url: str) -> Dict[str, List[Document]]:
        """Fetch and parse a GitHub pull request.

        Args:
            url (str): GitHub pull request URL

        Returns:
            Dict[str, List[Document]]: Dictionary with "documents" key containing list of Documents
        """
        pr_info = self._parse_pr_url(url)
        if not pr_info:
            error_msg = f"Invalid GitHub PR URL: {url}"
            logger.error(error_msg)
            if self.raise_on_failure:
                raise ValueError(error_msg)
            return {"documents": []}

        pr_data = self._fetch_pr_data(pr_info["owner"], pr_info["repo"], pr_info["pr_number"])
        if not pr_data:
            return {"documents": []}

        # Create document with PR content
        content = self._format_pr_content(pr_data)

        document = Document(
            content=content,
            meta={
                "url": url,
                "source": "github_pr",
                "pr_number": pr_data.get("number"),
                "title": pr_data.get("title"),
                "state": pr_data.get("state"),
                "user": pr_data.get("user", {}).get("login"),
                "created_at": pr_data.get("created_at"),
                "updated_at": pr_data.get("updated_at"),
                "merged_at": pr_data.get("merged_at"),
                "head_sha": pr_data.get("head", {}).get("sha"),
                "base_ref": pr_data.get("base", {}).get("ref"),
                "head_ref": pr_data.get("head", {}).get("ref"),
            },
        )

        return {"documents": [document]}

    def _format_pr_content(self, pr_data: Dict) -> str:
        """Format PR data into readable content."""
        content_parts = []

        # Title
        title = pr_data.get("title", "")
        content_parts.append(f"# {title}")

        # Basic info
        content_parts.append(f"**PR Number:** #{pr_data.get('number', 'N/A')}")
        content_parts.append(f"**State:** {pr_data.get('state', 'N/A')}")
        content_parts.append(f"**Author:** {pr_data.get('user', {}).get('login', 'N/A')}")
        content_parts.append(f"**Created:** {pr_data.get('created_at', 'N/A')}")
        content_parts.append(f"**Updated:** {pr_data.get('updated_at', 'N/A')}")

        # Branch info
        base_ref = pr_data.get("base", {}).get("ref", "N/A")
        head_ref = pr_data.get("head", {}).get("ref", "N/A")
        content_parts.append(f"**Branches:** {head_ref} → {base_ref}")

        # Merge status
        if pr_data.get("merged"):
            content_parts.append(f"**Merged:** {pr_data.get('merged_at', 'N/A')}")

        # Description/body
        body = pr_data.get("body")
        if body:
            content_parts.append("\n## Description")
            content_parts.append(body)

        # Stats
        content_parts.append("\n## Statistics")
        content_parts.append(f"**Commits:** {pr_data.get('commits', 'N/A')}")
        content_parts.append(f"**Additions:** {pr_data.get('additions', 'N/A')}")
        content_parts.append(f"**Deletions:** {pr_data.get('deletions', 'N/A')}")
        content_parts.append(f"**Changed Files:** {pr_data.get('changed_files', 'N/A')}")

        return "\n\n".join(content_parts)
