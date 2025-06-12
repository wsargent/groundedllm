"""Test GitHub issue content resolver component."""

from unittest.mock import Mock, patch

from haystack import Document
from haystack.dataclasses import ByteStream
from haystack.utils import Secret

from components.github import GithubIssueContentResolver


class TestGithubIssueContentResolver:
    """Test cases for GithubIssueContentResolver component."""

    def test_init_default_params(self):
        """Test component initialization with default parameters."""
        resolver = GithubIssueContentResolver()

        assert resolver.github_token is None
        assert resolver.raise_on_failure is False
        assert resolver.issue_regex is not None

    def test_init_with_params(self):
        """Test component initialization with custom parameters."""
        token = Secret.from_token("test_token")
        resolver = GithubIssueContentResolver(github_token=token, raise_on_failure=True)

        assert resolver.github_token == token
        assert resolver.raise_on_failure is True

    def test_can_handle_valid_github_issue_urls(self):
        """Test that can_handle correctly identifies valid GitHub issue URLs."""
        resolver = GithubIssueContentResolver()

        valid_urls = [
            "https://github.com/owner/repo/issues/123",
            "https://www.github.com/owner/repo/issues/456",
            "https://m.github.com/owner/repo/issues/789",
            "http://github.com/owner/repo/issues/101",
            "https://github.com/owner/repo/issues/123?tab=timeline",
            "https://github.com/owner/repo/issues/123#issuecomment-456",
            "https://github.com/owner-with-dash/repo-name/issues/999",
            "https://github.com/owner123/repo_name/issues/1",
        ]

        for url in valid_urls:
            assert resolver.can_handle(url), f"Should handle URL: {url}"

    def test_can_handle_invalid_urls(self):
        """Test that can_handle correctly rejects invalid URLs."""
        resolver = GithubIssueContentResolver()

        invalid_urls = [
            "https://github.com/owner/repo/pull/123",
            "https://github.com/owner/repo",
            "https://github.com/owner/repo/issues",
            "https://github.com/owner/repo/issues/abc",
            "https://gitlab.com/owner/repo/issues/123",
            "https://bitbucket.org/owner/repo/issues/123",
            "not-a-url",
            "",
            "https://github.com/owner/repo/wiki",
            "https://github.com/owner/repo/commit/abc123",
        ]

        for url in invalid_urls:
            assert not resolver.can_handle(url), f"Should not handle URL: {url}"

    @patch("components.github.GitHubIssueViewer")
    @patch("components.github.read_resource_file")
    @patch("components.github.PromptBuilder")
    def test_run_successful_single_url(self, mock_prompt_builder, mock_read_resource, mock_viewer_class):
        """Test successful processing of a single GitHub issue URL."""
        # Setup mocks
        mock_read_resource.return_value = "Test template: {{ documents }}"

        mock_prompt_builder_instance = Mock()
        mock_prompt_builder_instance.run.return_value = {"prompt": "Formatted issue content"}
        mock_prompt_builder.return_value = mock_prompt_builder_instance

        mock_viewer_instance = Mock()
        issue_doc = Document(content="Issue description", meta={"type": "issue", "title": "Test Issue", "author": "testuser", "url": "https://github.com/owner/repo/issues/123"})
        comment_doc = Document(content="Comment text", meta={"type": "comment", "author": "commenter"})
        mock_viewer_instance.run.return_value = {"documents": [issue_doc, comment_doc]}
        mock_viewer_class.return_value = mock_viewer_instance

        # Run test
        resolver = GithubIssueContentResolver()
        result = resolver.run(urls=["https://github.com/owner/repo/issues/123"])

        # Assertions
        assert isinstance(result, dict)
        assert "streams" in result
        assert len(result["streams"]) == 1
        assert isinstance(result["streams"][0], ByteStream)
        assert result["streams"][0].mime_type == "text/markdown"

        # Verify viewer was called correctly
        mock_viewer_class.assert_called_once_with(github_token=None, raise_on_failure=False, retry_attempts=2)
        mock_viewer_instance.run.assert_called_once_with("https://github.com/owner/repo/issues/123")

        # Verify prompt builder was used
        mock_prompt_builder.assert_called_once_with(template="Test template: {{ documents }}", required_variables=["documents"])
        mock_prompt_builder_instance.run.assert_called_once_with(documents=[issue_doc, comment_doc])

    @patch("components.github.GitHubIssueViewer")
    @patch("components.github.read_resource_file")
    @patch("components.github.PromptBuilder")
    def test_run_multiple_urls(self, mock_prompt_builder, mock_read_resource, mock_viewer_class):
        """Test processing multiple GitHub issue URLs."""
        # Setup mocks
        mock_read_resource.return_value = "Template"

        mock_prompt_builder_instance = Mock()
        mock_prompt_builder_instance.run.return_value = {"prompt": "Content"}
        mock_prompt_builder.return_value = mock_prompt_builder_instance

        mock_viewer_instance = Mock()
        doc = Document(content="Content", meta={"type": "issue"})
        mock_viewer_instance.run.return_value = {"documents": [doc]}
        mock_viewer_class.return_value = mock_viewer_instance

        # Run test
        resolver = GithubIssueContentResolver()
        urls = ["https://github.com/owner/repo/issues/123", "https://github.com/owner/repo/issues/456"]
        result = resolver.run(urls=urls)

        # Assertions
        assert isinstance(result, dict)
        assert "streams" in result
        assert len(result["streams"]) == 2
        assert all(isinstance(stream, ByteStream) for stream in result["streams"])
        assert mock_viewer_instance.run.call_count == 2

    @patch("components.github.GitHubIssueViewer")
    @patch("components.github.read_resource_file")
    @patch("components.github.PromptBuilder")
    def test_run_no_documents_returned(self, mock_prompt_builder, mock_read_resource, mock_viewer_class):
        """Test handling when GitHubIssueViewer returns no documents."""
        # Setup mocks
        mock_read_resource.return_value = "Template"
        mock_prompt_builder.return_value = Mock()

        mock_viewer_instance = Mock()
        mock_viewer_instance.run.return_value = {}  # No documents key
        mock_viewer_class.return_value = mock_viewer_instance

        # Run test
        resolver = GithubIssueContentResolver()
        result = resolver.run(urls=["https://github.com/owner/repo/issues/123"])

        # Should return empty dict with empty streams when no documents
        assert result == {"streams": []}

    @patch("components.github.GitHubIssueViewer")
    @patch("components.github.read_resource_file")
    @patch("components.github.PromptBuilder")
    def test_run_no_prompt_content(self, mock_prompt_builder, mock_read_resource, mock_viewer_class):
        """Test handling when prompt builder returns no content."""
        # Setup mocks
        mock_read_resource.return_value = "Template"

        mock_prompt_builder_instance = Mock()
        mock_prompt_builder_instance.run.return_value = {}  # No prompt key
        mock_prompt_builder.return_value = mock_prompt_builder_instance

        mock_viewer_instance = Mock()
        doc = Document(content="Content", meta={"type": "issue"})
        mock_viewer_instance.run.return_value = {"documents": [doc]}
        mock_viewer_class.return_value = mock_viewer_instance

        # Run test
        resolver = GithubIssueContentResolver()
        result = resolver.run(urls=["https://github.com/owner/repo/issues/123"])

        # Should return empty dict with empty streams when no prompt content
        assert result == {"streams": []}

    @patch("components.github.GitHubIssueViewer")
    @patch("components.github.read_resource_file")
    def test_run_with_github_token(self, mock_read_resource, mock_viewer_class):
        """Test that GitHub token is passed to viewer correctly."""
        mock_read_resource.return_value = "Test template: {{ documents }}"

        token = Secret.from_token("test_token")
        resolver = GithubIssueContentResolver(github_token=token, raise_on_failure=True)

        mock_viewer_instance = Mock()
        mock_viewer_instance.run.return_value = {}
        mock_viewer_class.return_value = mock_viewer_instance

        resolver.run(urls=["https://github.com/owner/repo/issues/123"])

        mock_viewer_class.assert_called_once_with(github_token=token, raise_on_failure=True, retry_attempts=2)

    @patch("components.github.logger")
    @patch("components.github.GitHubIssueViewer")
    @patch("components.github.read_resource_file")
    def test_logging_behavior(self, mock_read_resource, mock_viewer_class, mock_logger):
        """Test that appropriate logging occurs."""
        mock_read_resource.return_value = "Test template: {{ documents }}"

        # Test debug logging
        resolver = GithubIssueContentResolver()
        mock_viewer_instance = Mock()
        mock_viewer_instance.run.return_value = {}
        mock_viewer_class.return_value = mock_viewer_instance

        urls = ["https://github.com/owner/repo/issues/123"]
        resolver.run(urls=urls)

        # Check that the first debug call was made
        debug_calls = mock_logger.debug.call_args_list
        assert any(f"Using GithubIssueContentResolver for urls: {urls}" in str(call) for call in debug_calls)
        mock_logger.warning.assert_called_with("Using GithubIssueContentResolver: no documents in https://github.com/owner/repo/issues/123")

    def test_regex_pattern_compilation(self):
        """Test that the regex pattern is compiled correctly."""
        resolver = GithubIssueContentResolver()

        # Test that the regex object has expected methods
        assert hasattr(resolver.issue_regex, "match")
        assert hasattr(resolver.issue_regex, "pattern")

        # Test regex pattern matches expected structure
        test_url = "https://github.com/owner/repo/issues/123"
        match = resolver.issue_regex.match(test_url)
        assert match is not None
        assert match.groups() == ("owner", "repo", "123")

    @patch("components.github.GitHubIssueViewer")
    def test_viewer_initialization_parameters(self, mock_viewer_class):
        """Test that GitHubIssueViewer is initialized with correct parameters."""
        token = Secret.from_token("test_token")
        resolver = GithubIssueContentResolver(github_token=token, raise_on_failure=True)

        mock_viewer_instance = Mock()
        mock_viewer_instance.run.return_value = {}
        mock_viewer_class.return_value = mock_viewer_instance

        resolver.run(urls=["https://github.com/owner/repo/issues/123"])

        # Verify GitHubIssueViewer was initialized with correct parameters
        mock_viewer_class.assert_called_once_with(github_token=token, raise_on_failure=True, retry_attempts=2)

    def test_component_output_types(self):
        """Test that component has correct output types defined."""
        resolver = GithubIssueContentResolver()

        # Check that the component is properly decorated as a Haystack component
        # The @component decorator adds these properties
        assert hasattr(resolver, "run")
        assert callable(resolver.run)

        # Verify it's a proper Haystack component by checking its string representation
        component_str = str(resolver)
        assert "GithubIssueContentResolver" in component_str
        assert "Inputs:" in component_str
        assert "Outputs:" in component_str
        assert "streams: List[ByteStream]" in component_str
