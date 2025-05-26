# Make the conversation record more informative

see src/agent/agent.py
line 94:

   llm = self.llm_provider.start_conversation()

Right after this, I want to pass the instruction to the llm, so that it can record it as metadata on the conversation, like this:

llm.record_metadata("instruction", instruction)

That instruction should wind up in the conversation history's metadata section

## Plan:

put the implementation plan here. Do not change code yet.