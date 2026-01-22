"""
Tests for the chat service.
"""

import pytest
from src.services.chat import (
    ChatService,
    ChatRequest,
    ChatMessage,
    ChatResponse,
)


class TestChatService:
    """Tests for the ChatService class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ChatService()

    @pytest.mark.asyncio
    async def test_chat_greeting(self):
        """Test chat response for greeting."""
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="Hello!")],
        )
        response = await self.service.chat(request)

        assert response is not None
        assert response.message is not None
        assert len(response.message) > 0

    @pytest.mark.asyncio
    async def test_chat_help_request(self):
        """Test chat response for help request."""
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="What can you help me with?")],
        )
        response = await self.service.chat(request)

        assert response is not None
        assert response.message is not None

    @pytest.mark.asyncio
    async def test_chat_causal_question(self):
        """Test chat response for causal question."""
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="What is causal inference?")],
        )
        response = await self.service.chat(request)

        assert response is not None
        assert response.message is not None

    @pytest.mark.asyncio
    async def test_chat_with_context(self):
        """Test chat response with query context."""
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="What do these results mean?")],
            query_context={
                "domain": "complicated",
                "causal_result": {
                    "effect": 0.35,
                    "pValue": 0.02,
                    "confidenceInterval": [0.15, 0.55]
                }
            },
        )
        response = await self.service.chat(request)

        assert response is not None
        assert response.message is not None

    @pytest.mark.asyncio
    async def test_chat_response_has_suggestions(self):
        """Test that chat responses can include suggestions."""
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="How can I improve my analysis?")],
        )
        response = await self.service.chat(request)

        assert response is not None
        # suggestions may be None or a list
        assert response.suggestions is None or isinstance(response.suggestions, list)

    @pytest.mark.asyncio
    async def test_chat_bayesian_question(self):
        """Test chat response for Bayesian question."""
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="Explain epistemic uncertainty")],
        )
        response = await self.service.chat(request)

        assert response is not None
        assert response.message is not None

    @pytest.mark.asyncio
    async def test_chat_guardian_question(self):
        """Test chat response for Guardian question."""
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="What is the Guardian checking?")],
        )
        response = await self.service.chat(request)

        assert response is not None
        assert response.message is not None

    @pytest.mark.asyncio
    async def test_chat_conversation_history(self):
        """Test handling of conversation history."""
        request = ChatRequest(
            messages=[
                ChatMessage(role="user", content="Hello"),
                ChatMessage(role="assistant", content="Hi! How can I help?"),
                ChatMessage(role="user", content="What is causal inference?"),
            ],
        )
        response = await self.service.chat(request)

        assert response is not None
        assert response.message is not None

    @pytest.mark.asyncio
    async def test_chat_with_result_context(self):
        """Test chat with full result context."""
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="Show me the causal results")],
            query_context={
                "causal_result": {"effect": 0.42}
            },
        )
        response = await self.service.chat(request)

        assert response is not None
        # linked_panels should be a list or None
        assert response.linked_panels is None or isinstance(response.linked_panels, list)

    @pytest.mark.asyncio
    async def test_chat_response_confidence(self):
        """Test that chat responses include confidence."""
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="Tell me about my results")],
            query_context={"domain": "complex"},
        )
        response = await self.service.chat(request)

        assert response is not None
        # confidence may be None or a string
        assert response.confidence is None or isinstance(response.confidence, str)

    @pytest.mark.asyncio
    async def test_chat_custom_system_prompt(self):
        """Test chat with custom system prompt."""
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="Test message")],
            system_prompt="You are a helpful CARF assistant focused on causal analysis.",
        )
        response = await self.service.chat(request)

        assert response is not None
        assert response.message is not None

    @pytest.mark.asyncio
    async def test_chat_max_tokens(self):
        """Test chat with max tokens parameter."""
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="Give a brief explanation")],
            max_tokens=256,
        )
        response = await self.service.chat(request)

        assert response is not None
        assert response.message is not None


class TestChatServiceEdgeCases:
    """Edge case tests for ChatService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ChatService()

    @pytest.mark.asyncio
    async def test_empty_message_content(self):
        """Test handling of empty message content."""
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="")],
        )
        response = await self.service.chat(request)

        # Should still return a response
        assert response is not None

    @pytest.mark.asyncio
    async def test_long_conversation_history(self):
        """Test handling of long conversation history."""
        messages = []
        for i in range(10):
            messages.append(ChatMessage(role="user", content=f"Question {i}"))
            messages.append(ChatMessage(role="assistant", content=f"Answer {i}"))
        messages.append(ChatMessage(role="user", content="Final question"))

        request = ChatRequest(messages=messages)
        response = await self.service.chat(request)

        assert response is not None
        assert response.message is not None

    @pytest.mark.asyncio
    async def test_empty_context(self):
        """Test chat with empty context dict."""
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="Test")],
            query_context={},
        )
        response = await self.service.chat(request)

        assert response is not None
