import ollama
import json
from typing import List, Optional, Dict, Any


class AIGenerator:
    """Handles interactions with Ollama API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- **One search per query maximum**
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, host: str, model: str):
        self.client = ollama.Client(host=host)
        self.model = model

    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": query},
        ]

        # Build API call parameters
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }

        if tools:
            kwargs["tools"] = tools

        # Get response from Ollama
        response = self.client.chat(**kwargs)

        # Handle tool execution if needed
        if response["message"].get("tool_calls") and tool_manager:
            return self._handle_tool_execution(response, messages, tool_manager)

        return response["message"]["content"]

    def _handle_tool_execution(self, initial_response, messages: List[Dict], tool_manager):
        """
        Handle execution of tool calls and get follow-up response.

        Args:
            initial_response: The response containing tool use requests
            messages: Conversation messages so far
            tool_manager: Manager to execute tools

        Returns:
            Final response text after tool execution
        """
        # Add assistant's tool call message
        messages.append(initial_response["message"])

        # Execute each tool call and add results
        for tool_call in initial_response["message"]["tool_calls"]:
            tool_name = tool_call["function"]["name"]
            tool_args = tool_call["function"]["arguments"]

            tool_result = tool_manager.execute_tool(tool_name, **tool_args)

            messages.append({
                "role": "tool",
                "content": tool_result,
            })

        # Get final response without tools
        final_response = self.client.chat(
            model=self.model,
            messages=messages,
        )

        return final_response["message"]["content"]
