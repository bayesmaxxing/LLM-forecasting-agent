from swarm import Agent
# import from tools here

# Main Agent
main_agent = Agent(
    name = "Main Agent",
    instructions = "Determine which agent is best suited to handle the user's request and transfer the conversation to that agent.",
)

query_agent = Agent(
    name = "Query Agent",
    instructions = "Write and execute a query to answer the user's question",
)

news_agent = Agent(
    name = "News Agent",
    instructions = "Analyze the news and provide the user with a summary."
)

### Functions to transfer between agents
def transfer_to_main():
    """Call to return to Main Agent if the agent cannot deal with the user request"""
    return main_agent 

def transfer_to_query():
    return query_agent 

def transfer_to_news():
    return news_agent 

### Agent functions 

