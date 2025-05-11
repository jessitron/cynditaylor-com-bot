import unittest
from src.llm.frank_llm.frank import Frank
from src.llm.conversation_partner import ConversationPartner
from src.conversation.types import Exchange, Prompt, Response, PromptMetadata

class TestFrank(unittest.TestCase):

    def test_get_response_for_prompt(self):
        # Create a list of exchanges for testing using the new Exchange type
        exchanges = [
            Exchange(
                id="exchange-1",
                prompt=Prompt(prompt_text="What is your name?", metadata=PromptMetadata()),
                response=Response(response_text="My name is Frank.")
            ),
            Exchange(
                id="exchange-2",
                prompt=Prompt(prompt_text="What is your favorite color?", metadata=PromptMetadata()),
                response=Response(response_text="My favorite color is blue.")
            )
        ]
        frank = Frank(exchanges)

        # Test the get_response_for_prompt method
        prompt1 = Prompt(prompt_text="What is your name?", metadata=PromptMetadata())
        response1 = frank.get_response_for_prompt(prompt1)
        self.assertEqual(response1.response_text, "My name is Frank.")

        prompt2 = Prompt(prompt_text="What is your favorite color?", metadata=PromptMetadata())
        response2 = frank.get_response_for_prompt(prompt2)
        self.assertEqual(response2.response_text, "My favorite color is blue.")

    def test_extract_instruction(self):
        frank = Frank([])  # Empty list of exchanges for this test

        # Test with a prompt that has an INSTRUCTION: marker
        prompt_with_marker = """
        You are an agent that modifies code in the cynditaylor-com website.
        You have access to tools that allow you to list files, read and write file contents.

        INSTRUCTION:
        Update the hero section on the homepage to include a new tagline.

        Please analyze the instruction and use the available tools to make the necessary changes.
        """
        expected_instruction1 = "Update the hero section on the homepage to include a new tagline."
        self.assertEqual(frank._extract_instruction(prompt_with_marker), expected_instruction1)

        # Test with a prompt that has no INSTRUCTION: marker
        prompt_without_marker = "Update the hero section on the homepage to include a new tagline."
        expected_instruction2 = "Update the hero section on the homepage to include a new tagline."
        self.assertEqual(frank._extract_instruction(prompt_without_marker), expected_instruction2)

        # Test with a multi-line instruction
        prompt_with_multiline = """
        You are an agent that modifies code.

        INSTRUCTION:
        Update the hero section
        on the homepage to include
        a new tagline.

        Please analyze the instruction.
        """
        # The actual extracted text will include the indentation from the multi-line string
        expected_instruction3 = "Update the hero section\n        on the homepage to include\n        a new tagline."
        self.assertEqual(frank._extract_instruction(prompt_with_multiline), expected_instruction3)

        # Test with an empty prompt
        empty_prompt = ""
        self.assertEqual(frank._extract_instruction(empty_prompt), "")
