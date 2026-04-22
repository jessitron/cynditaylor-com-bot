from agent.server import app, invoke

print(f"app: {type(app).__name__}")
print(f"entrypoint: {invoke.__name__}")
