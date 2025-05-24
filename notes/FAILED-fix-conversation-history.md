# Active work for Augment Agent right now

In this file, we will formulate a plan together. Separately, you will implement it.

Our goal now is to make Frank work smoothly with the conversation history.

If you run the app with `./run` you will see some warnings:

```
WARNING - Prompt mismatch at index 0
WARNING - Prompt mismatch at index 1
WARNING - Prompt mismatch at index 2
WARNING - Prompt mismatch at index 3
```

I created test_conversation as a copy of a conversation history.
It seems that the conversation history is not recording exactly what Frank sees. How can we fix the
conversation history to be accurate?

## For Jess to do 
... Auggie has tried a couple times to solve it, but no, this requires design thought.
There's the prompt with tools included and the prompt without, maybe? Follow the prompt
through construction. Get the conversation history consistent with what Frank sees.