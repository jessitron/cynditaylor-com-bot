# Get the tools to work in a specific directory

In agent.py, line 75, it says  # For file operations, adjust paths to be relative to website_dir

OMG this does not belong in the agent. Remove this section.

Instead, make the file_read and file_write and file_list tools work in that website_dir only. All their operations are relative to that directory.

## Plan

Put the plan here, first. Do not implement yet.
