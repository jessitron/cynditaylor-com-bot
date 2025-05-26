import unittest

from src.conversation.types import Conversation, Exchange, TextPrompt, FinalResponse
from src.agent.agent import WebsiteAgent
from src.llm.in_memory_frank_provider import InMemoryFrankProvider
from src.conversation.in_memory_logger import InMemoryConversationLogger
from tests.conversation_test_utils import ConversationTestCase

class TestMinimalConvo(ConversationTestCase):
    def test_minimal_conversation_with_no_tool_calls(self):
        # create a Conversation with one exchange
        expected_conversation = Conversation(
            tool_list=[],
            version="2.0",
            conversation_id="test-conversation-id", 
            system_prompt="You are an agent that answers riddles.",
            exchanges=[
                Exchange(
                    id="exchange-1",
                    prompt=TextPrompt(
                        text="Why did the monkey cross the road?"
                    ),
                    response=FinalResponse(
                        text="To get away with the food he just stole from you."
                    )
                )
            ]
        )

        # Create in-memory logger to capture what agent logs
        in_memory_logger = InMemoryConversationLogger()
        
        # Create in-memory Frank LLM provider with the logger
        frank_provider = InMemoryFrankProvider(expected_conversation, in_memory_logger)
        
        # Create agent with Frank provider
        agent = WebsiteAgent(frank_provider, website_dir="cynditaylor-com")
        
        # Execute the instruction (this should trigger Frank to replay the conversation)
        instruction = "Why did the monkey cross the road?"
        
        # Run the agent
        result = agent.execute_instruction(instruction)
        
        # Get the logged conversation
        logged_conversation = in_memory_logger.get_conversation()
        
        # Debug: print the metadata
        print(f"\nDEBUG: Logged conversation metadata: {logged_conversation.metadata}")
        
        # Compare conversations
        self.assert_conversations_match(expected_conversation, logged_conversation)
        
        # Verify we got a result
        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main()
