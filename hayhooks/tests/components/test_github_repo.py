"""Test GitHub repo content resolver component."""

from unittest.mock import Mock, patch

from haystack import Document
from haystack.dataclasses import ByteStream
from haystack.utils import Secret

from components.github import GithubRepoContentResolver


class TestGithubRepoContentResolver:
    """Test cases for GithubRepoContentResolver component."""

    def test_init_default_params(self):
        """Test component initialization with default parameters."""
        resolver = GithubRepoContentResolver()

        assert resolver.github_token is None
        assert resolver.raise_on_failure is False
        assert resolver.github_regex is not None

    def test_init_with_params(self):
        """Test component initialization with custom parameters."""
        token = Secret.from_token("test_token")
        resolver = GithubRepoContentResolver(github_token=token, raise_on_failure=True)

        assert resolver.github_token == token
        assert resolver.raise_on_failure is True

    def test_can_handle_valid_github_repo_urls(self):
        """Test that can_handle correctly identifies valid GitHub repo URLs."""
        resolver = GithubRepoContentResolver()

        valid_urls = [
            "https://github.com/owner/repo",
            "https://github.com/owner/repo/blob/main/README.md",
            "https://github.com/owner/repo/tree/main/src",
            "https://github.com/owner/repo/raw/main/file.txt",
            "https://github.com/owner/repo/commit/abc123/file.py",
            "github.com/owner/repo/blob/develop/src/main.py",
            "https://github.com/owner-with-dash/repo-name/tree/feature-branch/dir/file.js",
            "https://github.com/owner123/repo_name/blob/v1.0.0/package.json",
            "https://github.com/wsargent/recipellm/blob/main/README.md",
            "https://raw.githubusercontent.com/wsargent/jmxmvc/refs/heads/master/README.md",
            "https://raw.githubusercontent.com/octocat/Spoon-Knife/main/README.md",
            "http://raw.githubusercontent.com/torvalds/linux/master/Documentation/admin-guide/devices.rst",
            "raw.githubusercontent.com/owner/repo/main/file.py",
        ]

        for url in valid_urls:
            assert resolver.can_handle(url), f"Should handle URL: {url}"

    def test_can_handle_invalid_urls(self):
        """Test that can_handle correctly rejects invalid URLs."""
        resolver = GithubRepoContentResolver()

        invalid_urls = [
            "https://github.com/owner/repo/issues/123",
            "https://github.com/owner/repo/pull/123",
            "https://gitlab.com/owner/repo",
            "https://bitbucket.org/owner/repo",
            "not-a-url",
            "",
            "https://example.com",
            "ftp://github.com/owner/repo",
            "https://raw.example.com/owner/repo/main/file.py",
        ]

        for url in invalid_urls:
            assert not resolver.can_handle(url), f"Should not handle URL: {url}"

    def test_parse_github_url_basic_repo(self):
        """Test parsing basic repository URL."""
        resolver = GithubRepoContentResolver()

        result = resolver._parse_github_url("https://github.com/owner/repo")

        assert result == {
            "owner": "owner",
            "repository": "repo",
            "branch_or_commit": None,
            "path": None,
        }

    def test_parse_github_url_with_path(self):
        """Test parsing repository URL with file path."""
        resolver = GithubRepoContentResolver()

        result = resolver._parse_github_url("https://github.com/owner/repo/blob/main/src/file.py")

        assert result == {
            "owner": "owner",
            "repository": "repo",
            "branch_or_commit": "main",
            "path": "src/file.py",
        }

    def test_parse_github_url_tree_view(self):
        """Test parsing repository URL with tree view."""
        resolver = GithubRepoContentResolver()

        result = resolver._parse_github_url("https://github.com/owner/repo/tree/develop/docs")

        assert result == {
            "owner": "owner",
            "repository": "repo",
            "branch_or_commit": "develop",
            "path": "docs",
        }

    def test_parse_github_url_raw_file(self):
        """Test parsing raw file URL."""
        resolver = GithubRepoContentResolver()

        result = resolver._parse_github_url("https://github.com/owner/repo/raw/v1.0.0/config.json")

        assert result == {
            "owner": "owner",
            "repository": "repo",
            "branch_or_commit": "v1.0.0",
            "path": "config.json",
        }

    def test_parse_github_url_commit_view(self):
        """Test parsing commit view URL."""
        resolver = GithubRepoContentResolver()

        result = resolver._parse_github_url("https://github.com/owner/repo/commit/abc123def/src/main.py")

        assert result == {
            "owner": "owner",
            "repository": "repo",
            "branch_or_commit": "abc123def",
            "path": "src/main.py",
        }

    def test_parse_github_url_invalid(self):
        """Test parsing invalid GitHub URL."""
        resolver = GithubRepoContentResolver()

        result = resolver._parse_github_url("https://invalid-url.com")

        assert result is None

    def test_parse_raw_github_url_basic(self):
        """Test parsing basic raw GitHub URL."""
        resolver = GithubRepoContentResolver()

        result = resolver._parse_github_url("https://raw.githubusercontent.com/owner/repo/main/README.md")

        assert result == {
            "owner": "owner",
            "repository": "repo",
            "branch_or_commit": "main",
            "path": "README.md",
        }

    def test_parse_raw_github_url_with_subdirectory(self):
        """Test parsing raw GitHub URL with subdirectory path."""
        resolver = GithubRepoContentResolver()

        result = resolver._parse_github_url("https://raw.githubusercontent.com/owner/repo/develop/src/components/file.py")

        assert result == {
            "owner": "owner",
            "repository": "repo",
            "branch_or_commit": "develop",
            "path": "src/components/file.py",
        }

    def test_parse_raw_github_url_with_refs_heads(self):
        """Test parsing raw GitHub URL with refs/heads branch reference."""
        resolver = GithubRepoContentResolver()

        result = resolver._parse_github_url("https://raw.githubusercontent.com/wsargent/jmxmvc/refs/heads/master/README.md")

        assert result == {
            "owner": "wsargent",
            "repository": "jmxmvc",
            "branch_or_commit": "refs/heads/master",
            "path": "README.md",
        }

    def test_parse_raw_github_url_without_protocol(self):
        """Test parsing raw GitHub URL without protocol."""
        resolver = GithubRepoContentResolver()

        result = resolver._parse_github_url("raw.githubusercontent.com/owner/repo/main/file.txt")

        assert result == {
            "owner": "owner",
            "repository": "repo",
            "branch_or_commit": "main",
            "path": "file.txt",
        }

    @patch("components.github.GitHubRepoViewer")
    def test_run_successful_single_url(self, mock_viewer_class):
        """Test successful processing of a single GitHub repo URL."""
        # Setup mocks
        mock_viewer_instance = Mock()
        doc1 = Document(content="File content 1", meta={"path": "file1.py", "repo": "owner/repo"})
        doc2 = Document(content="File content 2", meta={"path": "file2.py", "repo": "owner/repo"})
        mock_viewer_instance.run.return_value = {"documents": [doc1, doc2]}
        mock_viewer_class.return_value = mock_viewer_instance

        # Run test
        resolver = GithubRepoContentResolver()
        result = resolver.run(urls=["https://github.com/owner/repo/blob/main/src/file.py"])

        # Assertions
        assert isinstance(result, dict)
        assert "streams" in result
        assert len(result["streams"]) == 2
        assert all(isinstance(stream, ByteStream) for stream in result["streams"])
        assert all(stream.mime_type == "text/x-python" for stream in result["streams"])

        # Verify viewer was called correctly
        mock_viewer_class.assert_called_once_with(github_token=None, raise_on_failure=False)
        mock_viewer_instance.run.assert_called_once_with(path="src/file.py", repo="owner/repo", branch="main")

    @patch("components.github.GitHubRepoViewer")
    def test_run_multiple_urls(self, mock_viewer_class):
        """Test processing multiple GitHub repo URLs."""
        # Setup mocks
        mock_viewer_instance = Mock()
        doc = Document(content="Content", meta={"path": "file.py"})
        mock_viewer_instance.run.return_value = {"documents": [doc]}
        mock_viewer_class.return_value = mock_viewer_instance

        # Run test
        resolver = GithubRepoContentResolver()
        urls = ["https://github.com/owner/repo1/blob/main/file1.py", "https://github.com/owner/repo2/tree/develop/src"]
        result = resolver.run(urls=urls)

        # Assertions
        assert isinstance(result, dict)
        assert "streams" in result
        assert len(result["streams"]) == 2
        assert all(isinstance(stream, ByteStream) for stream in result["streams"])
        assert mock_viewer_instance.run.call_count == 2

    @patch("components.github.GitHubRepoViewer")
    def test_run_no_documents_returned(self, mock_viewer_class):
        """Test handling when GitHubRepoViewer returns no documents."""
        # Setup mocks
        mock_viewer_instance = Mock()
        mock_viewer_instance.run.return_value = {}  # No documents key
        mock_viewer_class.return_value = mock_viewer_instance

        # Run test
        resolver = GithubRepoContentResolver()
        result = resolver.run(urls=["https://github.com/owner/repo"])

        # Should return empty dict with empty streams when no documents
        assert result == {"streams": []}

    @patch("components.github.GitHubRepoViewer")
    def test_run_with_github_token(self, mock_viewer_class):
        """Test that GitHub token is passed to viewer correctly."""
        token = Secret.from_token("test_token")
        resolver = GithubRepoContentResolver(github_token=token, raise_on_failure=True)

        mock_viewer_instance = Mock()
        mock_viewer_instance.run.return_value = {}
        mock_viewer_class.return_value = mock_viewer_instance

        resolver.run(urls=["https://github.com/owner/repo"])

        mock_viewer_class.assert_called_once_with(github_token=token, raise_on_failure=True)

    @patch("components.github.GitHubRepoViewer")
    def test_run_exception_handling_raise_on_failure_false(self, mock_viewer_class):
        """Test exception handling when raise_on_failure is False."""
        # Setup mocks to raise exception
        mock_viewer_class.side_effect = Exception("GitHub API error")

        # Run test
        resolver = GithubRepoContentResolver(raise_on_failure=False)
        result = resolver.run(urls=["https://github.com/owner/repo"])

        # Should return empty streams when exception occurs and raise_on_failure is False
        assert result == {"streams": []}

    @patch("components.github.GitHubRepoViewer")
    def test_run_exception_handling_raise_on_failure_true(self, mock_viewer_class):
        """Test exception handling when raise_on_failure is True."""
        # Setup mocks to raise exception
        mock_viewer_class.side_effect = Exception("GitHub API error")

        # Run test
        resolver = GithubRepoContentResolver(raise_on_failure=True)

        try:
            resolver.run(urls=["https://github.com/owner/repo"])
            assert False, "Should have raised exception"
        except Exception as e:
            assert str(e) == "GitHub API error"

    @patch("components.github.logger")
    @patch("components.github.GitHubRepoViewer")
    def test_logging_behavior(self, mock_viewer_class, mock_logger):
        """Test that appropriate logging occurs."""
        # Test debug logging
        resolver = GithubRepoContentResolver()
        mock_viewer_instance = Mock()
        mock_viewer_instance.run.return_value = {}
        mock_viewer_class.return_value = mock_viewer_instance

        urls = ["https://github.com/owner/repo"]
        resolver.run(urls=urls)

        # Check that the first debug call was made
        debug_calls = mock_logger.debug.call_args_list
        assert any(f"Using GithubIssueContentResolver for urls: {urls}" in str(call) for call in debug_calls)
        mock_logger.warning.assert_called_with("Using GithubRepoContentResolver: no documents in https://github.com/owner/repo")

    def test_regex_pattern_compilation(self):
        """Test that the regex pattern is compiled correctly."""
        resolver = GithubRepoContentResolver()

        # Test that the regex object has expected methods
        assert hasattr(resolver.github_regex, "match")
        assert hasattr(resolver.github_regex, "pattern")

        # Test regex pattern matches expected structure
        test_url = "https://github.com/owner/repo/blob/main/file.py"
        match = resolver.github_regex.match(test_url)
        assert match is not None
        assert match.groups() == ("owner", "repo", "main", "file.py")

    @patch("components.github.GitHubRepoViewer")
    def test_viewer_initialization_parameters(self, mock_viewer_class):
        """Test that GitHubRepoViewer is initialized with correct parameters."""
        token = Secret.from_token("test_token")
        resolver = GithubRepoContentResolver(github_token=token, raise_on_failure=True)

        mock_viewer_instance = Mock()
        mock_viewer_instance.run.return_value = {}
        mock_viewer_class.return_value = mock_viewer_instance

        resolver.run(urls=["https://github.com/owner/repo"])

        # Verify GitHubRepoViewer was initialized with correct parameters
        mock_viewer_class.assert_called_once_with(github_token=token, raise_on_failure=True)

    def test_component_output_types(self):
        """Test that component has correct output types defined."""
        resolver = GithubRepoContentResolver()

        # Check that the component is properly decorated as a Haystack component
        # The @component decorator adds these properties
        assert hasattr(resolver, "run")
        assert callable(resolver.run)

        # Verify it's a proper Haystack component by checking its string representation
        component_str = str(resolver)
        assert "GithubRepoContentResolver" in component_str
        assert "Inputs:" in component_str
        assert "Outputs:" in component_str
        assert "streams: List[ByteStream]" in component_str

    @patch("components.github.GitHubRepoViewer")
    def test_run_repo_url_without_path(self, mock_viewer_class):
        """Test processing repository URL without specific path."""
        # Setup mocks
        mock_viewer_instance = Mock()
        doc = Document(content="README content", meta={"path": "README.md"})
        mock_viewer_instance.run.return_value = {"documents": [doc]}
        mock_viewer_class.return_value = mock_viewer_instance

        # Run test
        resolver = GithubRepoContentResolver()
        result = resolver.run(urls=["https://github.com/owner/repo"])

        # Verify viewer was called with empty string for path and None for branch
        mock_viewer_instance.run.assert_called_once_with(path="", repo="owner/repo", branch=None)

        # Verify result
        assert len(result["streams"]) == 1
        assert result["streams"][0].mime_type == "text/markdown"

    @patch("components.github.GitHubRepoViewer")
    def test_run_with_different_branch_types(self, mock_viewer_class):
        """Test processing URLs with different branch/commit types."""
        # Setup mocks
        mock_viewer_instance = Mock()
        doc = Document(content="File content", meta={"path": "file.py"})
        mock_viewer_instance.run.return_value = {"documents": [doc]}
        mock_viewer_class.return_value = mock_viewer_instance

        resolver = GithubRepoContentResolver()

        # Test with branch name
        resolver.run(urls=["https://github.com/owner/repo/blob/feature-branch/file.py"])
        mock_viewer_instance.run.assert_called_with(path="file.py", repo="owner/repo", branch="feature-branch")

        # Reset mock
        mock_viewer_instance.reset_mock()

        # Test with commit hash
        resolver.run(urls=["https://github.com/owner/repo/blob/abc123def456/file.py"])
        mock_viewer_instance.run.assert_called_with(path="file.py", repo="owner/repo", branch="abc123def456")

        # Reset mock
        mock_viewer_instance.reset_mock()

        # Test with version tag
        resolver.run(urls=["https://github.com/owner/repo/blob/v1.2.3/file.py"])
        mock_viewer_instance.run.assert_called_with(path="file.py", repo="owner/repo", branch="v1.2.3")

    @patch("components.github.GitHubRepoViewer")
    def test_run_raw_github_url(self, mock_viewer_class):
        """Test processing raw GitHub URL."""
        # Setup mocks
        mock_viewer_instance = Mock()
        doc = Document(content="Raw file content", meta={"path": "README.md"})
        mock_viewer_instance.run.return_value = {"documents": [doc]}
        mock_viewer_class.return_value = mock_viewer_instance

        # Run test
        resolver = GithubRepoContentResolver()
        result = resolver.run(urls=["https://raw.githubusercontent.com/owner/repo/main/README.md"])

        # Verify viewer was called correctly with parsed raw URL
        mock_viewer_instance.run.assert_called_once_with(path="README.md", repo="owner/repo", branch="main")

        # Verify result
        assert len(result["streams"]) == 1
        assert result["streams"][0].mime_type == "text/markdown"

    @patch("components.github.GitHubRepoViewer")
    def test_run_mixed_github_urls(self, mock_viewer_class):
        """Test processing mixed regular and raw GitHub URLs."""
        # Setup mocks
        mock_viewer_instance = Mock()
        doc = Document(content="File content", meta={"path": "file.py"})
        mock_viewer_instance.run.return_value = {"documents": [doc]}
        mock_viewer_class.return_value = mock_viewer_instance

        # Run test with mixed URL types
        resolver = GithubRepoContentResolver()
        urls = ["https://github.com/owner/repo/blob/main/file.py", "https://raw.githubusercontent.com/owner/repo/main/README.md"]
        result = resolver.run(urls=urls)

        # Verify both URLs were processed
        assert len(result["streams"]) == 2
        assert mock_viewer_instance.run.call_count == 2

        # Verify calls were made with correct parameters
        calls = mock_viewer_instance.run.call_args_list
        assert calls[0] == ((), {"path": "file.py", "repo": "owner/repo", "branch": "main"})
        assert calls[1] == ((), {"path": "README.md", "repo": "owner/repo", "branch": "main"})
