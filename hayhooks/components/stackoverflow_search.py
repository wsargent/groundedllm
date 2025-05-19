import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional, Union

import httpx
from hayhooks import log as logger
from haystack import Document, component
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
            api_key: Stack Overflow API key
            access_token: Optional Stack Overflow access token for authenticated requests
            timeout: HTTP request timeout in seconds
        """
        self.is_enabled = True  # still enabled even if no API key
        self.timeout = timeout
        self.request_timestamps = []  # Track request timestamps for rate limiting
        try:
            self.api_key = api_key.resolve_value()
            self.access_token = access_token.resolve_value() if access_token else None
        except Exception as e:
            logger.error(f"No API key or access token: {e}")
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

    def _fetch_answers(self, question_id: int) -> List[Dict[str, Any]]:
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
                return self._fetch_answers(question_id)

            # {
            #     "owner": {
            #         "account_id": 8759033,
            #         "reputation": 1373,
            #         "user_id": 6549532,
            #         "user_type": "registered",
            #         "profile_image": "https://i.sstatic.net/39I1E.jpg?s=256",
            #         "display_name": "Kevin",
            #         "link": "https://stackoverflow.com/users/6549532/kevin"
            #     },
            #     "is_accepted": false,
            #     "score": 21,
            #     "last_activity_date": 1469499896,
            #     "creation_date": 1469499896,
            #     "answer_id": 38580137,
            #     "question_id": 3988788,
            #     "content_license": "CC BY-SA 3.0"
            # }
            logger.debug(f"_fetch_answers: url={url} params={params}")
            response = httpx.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            logger.debug(f"_fetch_answers: response = {json.dumps(response.json(), indent=2)}")
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

            # Fetch answers
            answers = self._fetch_answers(question["question_id"])

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
            logger.debug(f"_format_response: question={question}")

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

            # Create document for question
            question_content = f"# {question.get('title', 'Untitled Question')}\n\n{question.get('body', '')}"

            # Add answers to content
            for i, answer in enumerate(result.get("answers", [])):
                question_content += f"\n\n## Answer {i + 1}"
                if answer.get("is_accepted"):
                    question_content += " (Accepted)"
                question_content += f" - Score: {answer.get('score', 0)}\n\n{answer.get('body', '')}"

            # Create metadata
            meta = {
                "title": question.get("title"),
                "url": question.get("link"),
                "score": question.get("score"),
                "answer_count": question.get("answer_count"),
                "tags": question.get("tags", []),
                "creation_date": question.get("creation_date"),
                "question_id": question.get("question_id"),
            }

            documents.append(Document(content=question_content, meta=meta))

        return documents


@component
class StackOverflowStackTraceAnalyzer(StackOverflowBase):
    """Uses Stack Overflow to analyze stack traces and find relevant solutions."""

    @component.output_types(documents=List[Document], results_json=str, results_markdown=str)
    def run(self, stack_trace: str, language: str, include_comments: bool = False, limit: Optional[int] = None) -> Dict[str, Union[List[Document], str]]:
        """Analyze stack trace and find relevant solutions.

        Args:
            stack_trace: Stack trace to analyze
            language: Programming language
            include_comments: Include comments in results
            limit: Maximum number of results

        Returns:
            Dictionary containing documents
        """

        logger.debug(f"run: stack_trace={stack_trace} self.is_enabled={self.is_enabled}")

        if not self.is_enabled:
            return {"documents": [], "results_json": "[]", "results_markdown": ""}

        try:
            # Usually the first line contains the relevant error
            error_lines = stack_trace.split("\n")
            error_message = error_lines[0] if error_lines else stack_trace

            # Prepare search parameters
            params = self._prepare_base_params(q=error_message, tagged=language.lower(), sort="votes", order="desc", filter=DEFAULT_FILTER)

            # Execute search
            url = f"{STACKOVERFLOW_API}/search/advanced"

            if not self._check_rate_limit():
                logger.warning("Rate limit exceeded, waiting before retry...")
                import time

                time.sleep(RETRY_AFTER_MS / 1000)
                return self.run(stack_trace, language, include_comments, limit)

            headers = {"Accept-Encoding": "gzip,deflate"}
            logger.debug(f"run: url={url} params={params}")
            response = httpx.get(url, params=params, timeout=self.timeout, headers=headers)
            logger.debug(f"run: response = {response.text}")
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
