# TODO: create agent graph
import getpass
import os
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import ToolMessage, AIMessage
from langgraph.prebuilt import ToolNode, tools_condition
import json

memory = MemorySaver()

# Define tool and bind to model
@tool
def get_news(query: str):
    ask = AskNewsSDK(client_id=ask_client_id,
                     client_secret=ask_client_secret,
                     scopes=["news","chat","stories"])
    oai = OpenAI(api_key=oai_api_key)

    response = ask.news.search_news(
        query=query,
        n_articles=10,
        return_type="string",
        method="nl"
    )

    return response.as_string

@tool
def calculate_current_brier_score(id: int):
    """
    Fetches all forecast points for a forecast and calculates the Brier scores.
    :param id: the id of forecast to fetch.
    """
    load_dotenv()

    db_pass = os.getenv("DB_PASSWORD")
    host = os.getenv("HOST")

    with pg.connect(f'dbname=postgres user=postgres host={host} port=5432 password={db_pass}') as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                        SELECT point_forecast  
                        FROM forecast_points 
                        WHERE forecast_id={id}
                        """)

            forecast_points = cur.fetchall()
            forecast_points = [row[0] for row in forecast_points]
            brier_scores = {
                "resolves as yes": (forecast_points - 1) ** 2,
                "resolves as no": (forecast_points - 0) ** 2
            }
            return brier_scores

tools = [get_news]
tool_node = ToolNode(tools)
model = ChatAnthropic(model_name="claude-3-haiku-20240307")
tool_model = model.bind_tools(tools)

# define control flow
def should_continue(state: MessagesState):
    last_message = state["messages"][-1]
    if not last_message.tool_calls:
        return END
    return "action"

def call_model(state: MessagesState):
    response = tool_model.invoke(state["messages"])
    return {"messages": response}

# Define agent graph
agent_flow = StateGraph(MessagesState)
agent_flow.add_node("agent", call_model)
agent_flow.add_node("action", tool_node)

agent_flow.add_edge(START, "agent")
agent_flow.add_conditional_edges(
    "agent",
    should_continue,
    ["action",END]
)
agent_flow.add_edge("action", "agent")

app = agent_flow.compile(checkpointer=memory)

