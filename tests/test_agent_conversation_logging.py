import unittest
import os
from src.agent.agent import WebsiteAgent
from src.llm.in_memory_frank_provider import InMemoryFrankProvider
from src.llm.conversation_reader import ConversationReader
from src.conversation.in_memory_logger import InMemoryConversationLogger
from tests.conversation_test_utils import ConversationTestCase


class TestAgentConversationLogging(ConversationTestCase):
    def test_agent_logs_conversation_matching_frank_replay(self):
        """
        Test that verifies the agent logs a conversation that matches 
        the hard-coded conversation replayed by Frank LLM.
        
        Uses in-memory components to avoid file dependencies.
        """
        # Load the test conversation that Frank will replay
        conversation_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "test_conversations", 
            "test_conversation.json"
        )
        expected_conversation = ConversationReader(conversation_file).load_conversation()
        
        # Create in-memory logger to capture what agent logs
        in_memory_logger = InMemoryConversationLogger()
        
        # Create in-memory Frank LLM provider with the logger
        frank_provider = InMemoryFrankProvider(expected_conversation, in_memory_logger)
        
        # Create agent with Frank provider
        agent = WebsiteAgent(frank_provider, website_dir="cynditaylor-com")
        
        # Execute the instruction (this should trigger Frank to replay the conversation)
        instruction = "Update the hero section on the homepage to include a new tagline: 'Bringing your memories to life through art'"
        
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