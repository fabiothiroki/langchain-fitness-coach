from langchain.agents import create_agent
from langchain_ollama import ChatOllama

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"Return the weather in {city} in a joke."

agent = create_agent(
    model=ChatOllama(model="llama3.2"),
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)

if __name__ == "__main__":
    # Run the agent
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "what is the weather in sf"}]}
    )
    print(result["messages"][-1].content)