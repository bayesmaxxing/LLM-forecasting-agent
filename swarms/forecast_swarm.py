from asknews_sdk import AskNewsSDK
from openai import OpenAI
from swarm import Agent, Swarm
import psycopg as pg 
import os 
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
client = Swarm()
# Functions for agents here
def execute_query(query: str):
    """
    Executes a provided query in the database and returns the results
    @param: query - the SQL query to execute in the database.
    @returns: the result of executing the SQL query against the database
    """
    load_dotenv()
    db_pass = os.getenv("DB_PASSWORD")
    host = os.getenv("HOST")

    with pg.connect(f'dbname=postgres user=postgres host={host} port=5432 password={db_pass}') as conn:
        with conn.cursor() as cur:
            cur.execute(query)

            query_results = cur.fetchall()
            return query_results 

def calc_posterior(likelihood: float, prior: float, evidence: float):
    """
    Calculates the posterior probability using Bayes' rule given a likelihood, a prior, and some evidence.
    @param: likelihood - the likelihood of observing the evidence.
    @param: evidence - the probability of observing the evidence.
    @param: prior - the prior probability of the outcome.
    @returns: the Bayesian posterior according to (likelihood * prior) / evidence.
    """
    if evidence == 0: 
        return "Cannot have probabilities that are equal to 0"
    else:
        return (likelihood * prior) / evidence 

def get_news(query: str):
    """
    Get the news for a specific related event or question.
    @param: query - the news event, in the form of a sentence or keyword, to get news for.
    @returns: a list of dicts with news related to the query from the past 48 hours.
    """
    ask_client_id = os.getenv('ASK_CLIENT_ID')
    ask_client_secret = os.getenv('ASK_CLIENT_SECRET')
    oai_api_key = os.getenv('OPENAI_API_KEY')

    ask = AskNewsSDK(client_id=ask_client_id, 
                     client_secret=ask_client_secret,
                     scopes=["news", "chat", "stories"])
    oai = OpenAI(api_key=oai_api_key)
    
    response = ask.news.search_news(
        query=query, 
        n_articles=10,
        return_type='string',
        method="nl",
    )

    return response.as_string

def transfer_to_main():
    return main_agent

def transfer_to_news():
    return news_agent 

def transfer_to_bayes():
    return bayes_agent 

def transfer_to_query():
    return query_agent 


# agents
main_agent = Agent(
    name = "Main agent", 
    instruction = f"""You are to understand a users request and call a tool to transer the request to the
    agent that is most suitable to handle the request. You are allowed to ask the user to add more information 
    to help you determine which agent is most suitable for the request. Do not make any unreasonable assumptions on behalf
    of the user. 
    If the user request if about obtaining recent news about an event or a forecast, transfer to the News agent. 
    If the user wants help with calculating a Bayesian posterior, transfer to the Bayes agent.
    If the user asks a question about forecasts, forecast points or aggregate statistics of their forecasts, transfer them to Query agent.
    If any other agent has referred back to you, you'll have to get more information from the user before before you can return them to the correct agent.
    """,
    functions = [transfer_to_news, transfer_to_bayes, transfer_to_query],
)
db_schema = """Table: forecast_v2, fields:[id : unique integer for each forecast, question: string with the forecast question, category: string with one or more categories the forecast belongs to,
    created: datetime of question creation, resolution_criteria: string with information about the conditions for the forecast to resolve as  Yes or No, 
    resolution: string with information about how the forecast resolved. Is equal to "0" if the forecast did not happen, "1" is it happened and "-" if it resolved as ambiguous, 
    resolved: datetime of question resolution, brier_score: Brier score obtained from the forecast, log2_score: the Log score in base 2 obtained for the forecast,
    logn_score: the Log score in natural logarithm obtained for the forecast, comment: string comment from the user on the resolution], 
    Table: forecast_points, fields:[update_id: unique integer for the forecast point, forecast_id: the unique integer for each forecast, point_forecast: the forecasted probability as a float, 
    upper_ci: the upper confidence interval on the forecasted probability, lower_ci: the lower confidence interval on the forecasted probability, 
    reson: a string with the user's reason for the forecast point, created: datetime of forecast point creation]
    """

query_agent = Agent(
    name = "Query agent", 
    instruction = f"""You are to answer the user's question about their forecasts, forecast points, or aggregate statistics truthfully. To your help, you have the
    user's database. To use the database, write a query that gives you information the information that you need and pass it to the execute_query function.
    The database has the following structure {db_schema}.
    If you feel like the information you've got is not enough, transfer back to Main agent to obtain more information.
    """,
    functions = [execute_query, transfer_to_main],
)

news_agent = Agent(
    name = "News agent",
    instruction = f"""You are to determine what news the user is interested in finding. Based on that understanding, you'll create a 
    query to pass to the get_news function. If you feel like the information you've got is not enough to perform the news search, transfer back to Main agent to obtain more information.
    """, 
    functions = [get_news, transfer_to_main],
)

bayes_agent = Agent(
    name = "Bayes agent", 
    instruction = f"""You are to determine the user's likelihood, evidence, and prior from their request and use that for the calc_posterior function
    to help the user determine an appropriate forecast update.
    If you are unable to parse the user's likelihood, evidence and prior, transfer back to Main agent to obtain more information.
    """, 
    functions = [calc_posterior,transfer_to_main],
)

response = client.run(
        agent=main_agent,
        messages=[{"role":"user","content":"Hey, what's the latest news on Google and them being broken up?"}]
)

print(response.agent.name)
print(response.messages[-1]["content"])
print(response.messages[-1]["sender"])
