open_api_json_path = "openapischma.json"
project_endpoint = ""
mf_api_key = ""
openapi_conn_id = ""

import jsonref
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import OpenApiTool, OpenApiConnectionAuthDetails, OpenApiConnectionSecurityScheme
import time

client = AIProjectClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential()
)

# Load OpenAPI schema
with open(open_api_json_path, "r") as f:
    open_api_schema = jsonref.load(f)

# Authentication for OpenAPI connection
auth = OpenApiConnectionAuthDetails(
    security_scheme=OpenApiConnectionSecurityScheme(connection_id=openapi_conn_id)
)

# Create OpenAPI tool (CORRECTED: use single tool, not .definitions)
openapi_tool = OpenApiTool(
    name="OpenWeatherMapTool",
    description="Get weather data from OpenWeatherMap API",
    spec=open_api_schema,
    auth=auth
)

# Create agent
agent = client.agents.create_agent(
    model="gpt-4o",
    name="WeatherAgent",
    instructions="""You are a weather assistant. When users ask about weather, 
    use the OpenWeatherMapTool to get accurate current weather, forecasts, 
    or historical data for any location or coordinates provided.""",
    tools = openapi_tool.definitions  # Fixed: pass tool directly in list
)

print(f"Agent created with ID: {agent.id}")
thread = client.agents.threads.create()
print(f"Thread created with ID: {thread.id}")

print("I'm your weather assistant! Ask me about weather in any location or coordinates.")

try:
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        # Send user message
        message = client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )

        # Create and poll run (CORRECTED: wait for completion)
        run = client.agents.runs.create(
            thread_id=thread.id,
            agent_id=agent.id
        )

        # Poll until run completes
        while run.status in ["queued", "in_progress"]:
            time.sleep(1)
            run = client.agents.runs.get(
                thread_id=thread.id,
                run_id=run.id
            )

        if run.status == "failed":
            print(f"Run failed: {run.last_error}")
            continue

        # Get latest agent message (CORRECTED: proper response extraction)
        messages = client.agents.messages.list(thread_id=thread.id)
        agent_message = next(messages)  # Newest first
        
        # Handle structured or text response
        if agent_message.content and agent_message.content[0].text:
            content = agent_message.content[0].text
            response = content.value if hasattr(content, 'value') else str(content)
            print(f"Agent: {response}")
        else:
            print("Agent: No response content found")

except Exception as e:
    print(f"Error: {e}")
finally:
    client.agents.delete_agent(agent.id)
    print("Agent deleted.")
