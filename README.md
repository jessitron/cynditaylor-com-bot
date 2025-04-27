# Cyndi Taylor Website Bot

This project implements an automated agent that helps Cyndi Taylor update her website (cynditaylor.com) without requiring technical knowledge.

## Workflow

```mermaid
graph TD
    A[Cyndi Taylor] -->|Sends email/text with instructions and attachments| B[Website Bot Agent]
    B -->|Checks out code from GitHub| C[Website Repository]
    B -->|Makes requested changes| C
    B -->|Commits and pushes changes| D[GitHub]
    D -->|GitHub Actions| E[Build and Deploy]
    E -->|Publishes to| F[GitHub Pages]
    F -->|Website updated| G[cynditaylor.com]
    B -->|Monitors deployment| D
    B -->|Sends confirmation| A
    A -->|Provides feedback| B
    B -->|Records feedback| H[Feedback Log]
    A -->|Requests further changes| B
```

## Purpose

This agent serves as an intermediary between Cyndi Taylor and her website's codebase. It allows her to:

1. Request changes to her website through simple instructions
2. Upload new images of paintings
3. Update content and styling
4. Receive confirmation when changes are live
5. Provide feedback on the changes

The agent handles all the technical aspects of:
- Code modification
- Version control
- Deployment
- Monitoring
- Communication

## Implementation

This project implements the agent that processes requests, makes the appropriate code changes, and manages the deployment process.

## Setup

[Setup instructions will be added as the project develops]
