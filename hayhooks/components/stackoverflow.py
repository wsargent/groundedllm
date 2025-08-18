import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional, Union

import httpx
from hayhooks import log as logger
from haystack import Document, component
from haystack.dataclasses import ByteStream
from haystack.utils import Secret

## Shamelessly stolen from https://github.com/gscalzo/stackoverflow-mcp/blob/main/src/index.ts
DEFAULT_FILTER = "withbody"  # Custom filter for questions with bodies
ANSWER_FILTER = "withbody"  # Custom filter for answers with bodies
COMMENT_FILTER = "withbody"  # Custom filter for comments

# Rate limiting configuration
MAX_REQUESTS_PER_WINDOW = 30  # Maximum requests per window
RATE_LIMIT_WINDOW_MS = 60000  # Window size in milliseconds (1 minute)
RETRY_AFTER_MS = 2000  # Time to wait before retrying after rate limit
DEFAULT_TIMEOUT = 10  # Default timeout in seconds

# Stack Overflow API base URL
STACKOVERFLOW_API = "https://api.stackexchange.com/2.3"


class StackOverflowBase:
    """Base class for Stack Overflow components with shared functionality."""

    def __init__(self, api_key: Secret = Secret.from_env_var("STACKOVERFLOW_API_KEY"), access_token: Optional[Secret] = None, timeout: int = DEFAULT_TIMEOUT):
        """Initialize the Stack Overflow component.

        Args:
            api_key (Secret): Stack Overflow API key
            access_token (Optional[Secret]): Optional Stack Overflow access token for authenticated requests
            timeout (int): HTTP request timeout in seconds
        """
        self.is_enabled = True  # still enabled even if no API key
        self.timeout = timeout
        self.request_timestamps = []  # Track request timestamps for rate limiting
        try:
            self.api_key = api_key.resolve_value()
            self.access_token = access_token.resolve_value() if access_token else None
        except Exception:
            logger.info("STACKOVERFLOW_API_KEY is not set, rate limit for queries will be lower.")
            self.api_key = None
            self.access_token = None

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = datetime.now()
        # Remove timestamps outside the window
        self.request_timestamps = [timestamp for timestamp in self.request_timestamps if now - timestamp < timedelta(milliseconds=RATE_LIMIT_WINDOW_MS)]

        if len(self.request_timestamps) >= MAX_REQUESTS_PER_WINDOW:
            return False

        self.request_timestamps.append(now)
        return True

    def _prepare_base_params(self, **kwargs) -> Dict[str, Any]:
        """Prepare base parameters for Stack Overflow API requests."""
        params = {"site": "stackoverflow", **kwargs}

        if self.api_key:
            params["key"] = self.api_key

        if self.access_token:
            params["access_token"] = self.access_token

        return params

    async def _fetch_answers_async(self, question_id: int) -> List[Dict[str, Any]]:
        """Fetch answers for a specific question asynchronously."""
        if not self.is_enabled:
            return []

        params = self._prepare_base_params(filter=ANSWER_FILTER, sort="votes", order="desc")

        url = f"{STACKOVERFLOW_API}/questions/{question_id}/answers"

        try:
            if not self._check_rate_limit():
                logger.warning("Rate limit exceeded, waiting before retry...")
                await asyncio.sleep(RETRY_AFTER_MS / 1000)
                return await self._fetch_answers_async(question_id)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                return data.get("items", [])
        except Exception as e:
            logger.error(f"Error fetching answers for question {question_id}: {e}")
            return []

    def fetch_answers(self, question_id: int) -> List[Dict[str, Any]]:
        """Fetch answers for a specific question synchronously."""
        if not self.is_enabled:
            return []

        params = self._prepare_base_params(filter=ANSWER_FILTER, sort="votes", order="desc")

        url = f"{STACKOVERFLOW_API}/questions/{question_id}/answers"

        try:
            if not self._check_rate_limit():
                logger.warning("Rate limit exceeded, waiting before retry...")
                import time

                time.sleep(RETRY_AFTER_MS / 1000)
                return self.fetch_answers(question_id)

            logger.debug(f"_fetch_answers: url={url} params={params}")
            response = httpx.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            # logger.debug(f"_fetch_answers: response = {json.dumps(response.json(), indent=2)}")
            data = response.json()
            return data.get("items", [])
        except Exception as e:
            logger.error(f"Error fetching answers for question {question_id}: {e}")
            return []

    async def _fetch_comments_async(self, post_id: int) -> List[Dict[str, Any]]:
        """Fetch comments for a specific post asynchronously."""
        if not self.is_enabled:
            return []

        params = self._prepare_base_params(filter=COMMENT_FILTER, sort="votes", order="desc")

        url = f"{STACKOVERFLOW_API}/posts/{post_id}/comments"

        try:
            if not self._check_rate_limit():
                logger.warning("Rate limit exceeded, waiting before retry...")
                await asyncio.sleep(RETRY_AFTER_MS / 1000)
                return await self._fetch_comments_async(post_id)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                return data.get("items", [])
        except Exception as e:
            logger.error(f"Error fetching comments for post {post_id}: {e}")
            return []

    def _fetch_comments(self, post_id: int) -> List[Dict[str, Any]]:
        """Fetch comments for a specific post synchronously."""
        if not self.is_enabled:
            return []

        params = self._prepare_base_params(filter=COMMENT_FILTER, sort="votes", order="desc")

        url = f"{STACKOVERFLOW_API}/posts/{post_id}/comments"

        try:
            if not self._check_rate_limit():
                logger.warning("Rate limit exceeded, waiting before retry...")
                import time

                time.sleep(RETRY_AFTER_MS / 1000)
                return self._fetch_comments(post_id)

            response = httpx.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except Exception as e:
            logger.error(f"Error fetching comments for post {post_id}: {e}")
            return []

    async def _process_search_results_async(self, questions: List[Dict[str, Any]], min_score: Optional[int] = None, include_comments: bool = False, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Process search results and fetch additional data asynchronously."""
        results = []

        # Apply limit if specified
        if limit is not None:
            questions = questions[:limit]

        for question in questions:
            # Skip questions below minimum score
            if min_score is not None and question.get("score", 0) < min_score:
                continue

            # Fetch answers
            answers = await self._fetch_answers_async(question["question_id"])

            result = {"question": question, "answers": answers}

            # Fetch comments if requested
            if include_comments:
                question_comments = await self._fetch_comments_async(question["question_id"])

                answers_comments = {}
                for answer in answers:
                    if "answer_id" in answer:
                        answers_comments[answer["answer_id"]] = await self._fetch_comments_async(answer["answer_id"])

                result["comments"] = {"question": question_comments, "answers": answers_comments}

            results.append(result)

        return results

    def _process_search_results(self, questions: List[Dict[str, Any]], min_score: Optional[int] = None, include_comments: bool = False, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Process search results and fetch additional data synchronously."""
        results = []

        # Apply limit if specified
        if limit is not None:
            questions = questions[:limit]

        for question in questions:
            # Skip questions below minimum score
            if min_score is not None and question.get("score", 0) < min_score:
                continue

            # logger.debug(f"_process_search_results: question={json.dumps(question, indent=2)}")

            # Fetch answers
            answers = self.fetch_answers(question["question_id"])
            # answers = []

            result = {"question": question, "answers": answers}

            # Fetch comments if requested
            if include_comments:
                question_comments = self._fetch_comments(question["question_id"])

                answers_comments = {}
                for answer in answers:
                    if "answer_id" in answer:
                        answers_comments[answer["answer_id"]] = self._fetch_comments(answer["answer_id"])

                result["comments"] = {"question": question_comments, "answers": answers_comments}

            results.append(result)

        return results

    def _format_response(self, results: List[Dict[str, Any]], response_format: Literal["json", "markdown"] = "json") -> str:
        """Format search results as JSON or Markdown."""
        if response_format == "json":
            return json.dumps(results, indent=2)

        # Format as markdown
        markdown = ""
        for result in results:
            question = result["question"]
            # logger.debug(f"_format_response: question={question}")

            markdown += f"# {question.get('title', 'Untitled Question')}\n\n"
            markdown += f"**Score:** {question.get('score', 0)} | **Answers:** {question.get('answer_count', 0)}\n\n"
            markdown += f"## Question\n\n{question.get('body', '')}\n\n"

            if "comments" in result and result["comments"].get("question"):
                markdown += "### Question Comments\n\n"
                for comment in result["comments"]["question"]:
                    markdown += f"- {comment.get('body', '')} *(Score: {comment.get('score', 0)})*\n"
                markdown += "\n"

            markdown += "## Answers\n\n"
            for answer in result.get("answers", []):
                markdown += f"### {'✓ ' if answer.get('is_accepted') else ''}Answer (Score: {answer.get('score', 0)})\n\n"
                markdown += f"{answer.get('body', '')}\n\n"

                if "comments" in result and answer.get("answer_id") in result["comments"].get("answers", {}):
                    markdown += "#### Answer Comments\n\n"
                    for comment in result["comments"]["answers"][answer.get("answer_id")]:
                        markdown += f"- {comment.get('body', '')} *(Score: {comment.get('score', 0)})*\n"
                    markdown += "\n"

            markdown += f"---\n\n[View on Stack Overflow]({question.get('link', '')})\n\n"

        return markdown

    def _create_documents_from_results(self, results: List[Dict[str, Any]]) -> List[Document]:
        """Convert search results to Haystack Document objects."""
        documents = []

        for result in results:
            question = result["question"]
            question_content = question.get("body", "")

            # Create metadata
            meta = {
                "title": question.get("title"),
                "url": question.get("link"),
                "score": question.get("score"),
                "answer_count": question.get("answer_count"),
                "tags": question.get("tags", []),
                "creation_date": question.get("creation_date"),
                "question_id": question.get("question_id"),
                "answers": result.get("answers", []),
            }
            documents.append(Document(content=question_content, meta=meta))

        return documents


@component
class StackOverflowErrorSearch(StackOverflowBase):
    """Uses Stack Overflow to search for error-related questions."""

    @component.output_types(documents=List[Document])
    def run(self, error_message: str, language: Optional[str] = None, technologies: Optional[List[str]] = None, min_score: Optional[int] = None, include_comments: bool = False, limit: Optional[int] = None) -> Dict[str, Union[List[Document], str]]:
        """Search Stack Overflow for error-related questions.

        Args:
            error_message (str): Error message to search for
            language (Optional[str]): Programming language
            technologies (Optional[List[str]]): Related technologies
            min_score (Optional[int]): Minimum score threshold
            include_comments (bool): Include comments in results
            limit (Optional[int]): Maximum number of results

        Returns:
            Dict[str, Union[List[Document], str]]: Dictionary containing documents
        """
        if not self.is_enabled:
            return {"documents": []}

        # Build tags list
        tags = []
        if language:
            tags.append(language.lower())
        if technologies:
            tags.extend([tech.lower() for tech in technologies])

        try:
            # https://api.stackexchange.com/docs/advanced-search
            # Prepare search parameters
            params = self._prepare_base_params(
                q=error_message, sort="relevance", order="desc", filter=DEFAULT_FILTER, **({"min": min_score} if min_score is not None else {}), **({"pagesize": str(limit)} if limit is not None else {}), **({"tagged": ";".join(tags)} if tags else {})
            )
            logger.debug(f"params={params}")

            # Execute search
            url = f"{STACKOVERFLOW_API}/search/advanced"

            if not self._check_rate_limit():
                logger.warning("Rate limit exceeded, waiting before retry...")
                import time

                time.sleep(RETRY_AFTER_MS / 1000)
                return self.run(error_message, language, technologies, min_score, include_comments, limit)

            response = httpx.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            # Process results
            results = self._process_search_results(data.get("items", []), min_score=min_score, include_comments=include_comments, limit=limit)

            markdown = self._format_response(results, "markdown")
            logger.debug(f"_process_search_results: results={markdown}")

            # Create documents
            documents = self._create_documents_from_results(results)

            return {"documents": documents}

        except Exception as e:
            logger.error(f"Error in stackoverflow: {e}")
            return {"documents": [], "results_json": "[]", "results_markdown": ""}

    @component.output_types(documents=List[Document])
    async def run_async(
        self, error_message: str, language: Optional[str] = None, technologies: Optional[List[str]] = None, min_score: Optional[int] = None, include_comments: bool = False, limit: Optional[int] = None
    ) -> Dict[str, Union[List[Document], str]]:
        """Asynchronously search Stack Overflow for error-related questions.

        Args:
            error_message (str): Error message to search for
            language (Optional[str]): Programming language
            technologies (Optional[List[str]]): Related technologies
            min_score (Optional[int]): Minimum score threshold
            include_comments (bool): Include comments in results
            limit (Optional[int]): Maximum number of results

        Returns:
            Dict[str, Union[List[Document], str]]: Dictionary containing documents
        """
        if not self.is_enabled:
            return {"documents": []}

        # Build tags list
        tags = []
        if language:
            tags.append(language.lower())
        if technologies:
            tags.extend([tech.lower() for tech in technologies])

        try:
            # Prepare search parameters
            params = self._prepare_base_params(
                q=error_message, sort="relevance", order="desc", filter=DEFAULT_FILTER, **({"min": min_score} if min_score is not None else {}), **({"pagesize": str(limit)} if limit is not None else {}), **({"tagged": ";".join(tags)} if tags else {})
            )

            # Execute search
            url = f"{STACKOVERFLOW_API}/search/advanced"

            if not self._check_rate_limit():
                logger.warning("Rate limit exceeded, waiting before retry...")
                await asyncio.sleep(RETRY_AFTER_MS / 1000)
                return await self.run_async(error_message, language, technologies, min_score, include_comments, limit)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

            # Process results
            results = await self._process_search_results_async(data.get("items", []), min_score=min_score, include_comments=include_comments, limit=limit)

            # Create documents
            documents = self._create_documents_from_results(results)

            return {"documents": documents}

        except Exception as e:
            logger.error(f"Error in stackoverflow (async): {e}")
            return {"documents": []}


@component
class StackOverflowStackTraceAnalyzer(StackOverflowBase):
    """Uses Stack Overflow to analyze stack traces and find relevant solutions."""

    @component.output_types(documents=List[Document])
    def run(self, stack_trace: str, language: str, include_comments: bool = False, limit: Optional[int] = None) -> Dict[str, Union[List[Document], str]]:
        """Analyze stack trace and find relevant solutions.

        Args:
            stack_trace (str): Stack trace to analyze
            language (str): Programming language
            include_comments (bool): Include comments in results
            limit (Optional[int]): Maximum number of results

        Returns:
            Dict[str, Union[List[Document], str]]: Dictionary containing documents
        """

        logger.debug(f"run: stack_trace={stack_trace} self.is_enabled={self.is_enabled}")

        if not self.is_enabled:
            return {"documents": [], "results_json": "[]", "results_markdown": ""}

        try:
            # Usually the first line contains the relevant error
            error_lines = stack_trace.split("\n")
            error_message = error_lines[0] if error_lines else stack_trace

            # Prepare search parameters
            params = self._prepare_base_params(q=error_message, tagged=language.lower(), sort="relevance", order="desc", filter=DEFAULT_FILTER, limit=limit)

            # Execute search
            url = f"{STACKOVERFLOW_API}/search/advanced"

            if not self._check_rate_limit():
                logger.warning("Rate limit exceeded, waiting before retry...")
                import time

                time.sleep(RETRY_AFTER_MS / 1000)
                return self.run(stack_trace, language, include_comments, limit)

            headers = {"Accept-Encoding": "gzip,deflate"}
            # logger.debug(f"run: url={url} params={params}")
            response = httpx.get(url, params=params, timeout=self.timeout, headers=headers)
            # logger.debug(f"run: response = {response.text}")
            response.raise_for_status()
            data = response.json()

            # Process results
            results = self._process_search_results(data.get("items", []), include_comments=include_comments, limit=limit)

            # Create documents
            documents = self._create_documents_from_results(results)

            return {"documents": documents}

        except Exception as e:
            logger.error(f"Error in analyze_stack_trace: {e}")
            return {"documents": [], "results_json": "[]", "results_markdown": ""}


@component
class StackOverflowContentResolver:
    """A resolver that uses the StackExchange API to fetch content from StackOverflow URLs."""

    def __init__(
        self,
        api_key: Secret = Secret.from_env_var("STACKOVERFLOW_API_KEY"),
        access_token: Optional[Secret] = None,
        timeout: int = DEFAULT_TIMEOUT,
        raise_on_failure: bool = False,
    ):
        self.raise_on_failure = raise_on_failure
        self.stackoverflow_client = StackOverflowBase(
            api_key=api_key,
            access_token=access_token,
            timeout=timeout,
        )

    @component.output_types(streams=List[ByteStream])
    def run(self, urls: List[str]):
        streams = []

        for url in urls:
            try:
                # Extract question ID from URL
                question_id = self._extract_question_id(url)
                if not question_id:
                    logger.warning(f"Could not extract question ID from {url}")
                    continue

                # Fetch question details
                params = self.stackoverflow_client._prepare_base_params(
                    filter="withbody",  # Include question body
                    site="stackoverflow",
                )
                api_url = f"{STACKOVERFLOW_API}/questions/{question_id}"

                response = httpx.get(api_url, params=params, timeout=self.stackoverflow_client.timeout)
                response.raise_for_status()
                data = response.json()

                if not data.get("items"):
                    logger.warning(f"No question found for ID {question_id}")
                    continue

                question = data["items"][0]

                # Fetch answers
                answers = self.stackoverflow_client.fetch_answers(question_id)

                # Combine question and answers into a single document
                result = {"question": question, "answers": answers}

                # Format the content as markdown
                content = self._format_as_markdown(result)

                # Create ByteStream
                stream = ByteStream(data=content.encode("utf-8"))
                stream.meta = {"url": url, "content_type": "text/markdown", "title": question.get("title", ""), "source": "stackoverflow"}
                stream.mime_type = "text/markdown"

                streams.append(stream)

            except Exception as e:
                logger.warning(f"Failed to fetch {url} using StackOverflow API: {str(e)}")
                if self.raise_on_failure:
                    raise e

        return {"streams": streams}

    def can_handle(self, url: str) -> bool:
        # Check if the URL is from StackOverflow
        return "stackoverflow.com/questions" in url

    def _extract_question_id(self, url: str) -> Optional[int]:
        """Extract the question ID from a StackOverflow URL."""
        import re

        # Match patterns like:
        # https://stackoverflow.com/questions/12345/title
        # https://stackoverflow.com/questions/12345
        match = re.search(r"stackoverflow\.com/questions/(\d+)", url)
        if match:
            return int(match.group(1))
        return None

    def _format_as_markdown(self, result: Dict) -> str:
        """Format the question and answers as markdown."""
        question = result["question"]
        answers = result["answers"]

        # Format question
        md = f"# {question.get('title', 'Untitled Question')}\n\n"
        md += f"**Score**: {question.get('score', 0)} | "
        md += f"**Asked by**: {question.get('owner', {}).get('display_name', 'Anonymous')} | "
        md += f"**Date**: {question.get('creation_date', '')}\n\n"
        md += question.get("body", "")
        md += "\n\n---\n\n"

        # Format answers
        md += f"## {len(answers)} Answers\n\n"

        # Sort answers by score (highest first)
        sorted_answers = sorted(answers, key=lambda x: x.get("score", 0), reverse=True)

        for i, answer in enumerate(sorted_answers):
            md += f"### Answer {i + 1} (Score: {answer.get('score', 0)})\n\n"
            md += f"**Answered by**: {answer.get('owner', {}).get('display_name', 'Anonymous')} | "
            md += f"**Date**: {answer.get('creation_date', '')}\n\n"
            md += answer.get("body", "")
            md += "\n\n---\n\n"

        return md
