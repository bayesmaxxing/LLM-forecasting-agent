from asknews_sdk import AskNewsSDK
from swarm import Agent, Swarm
import psycopg as pg 
import os 
from dotenv import load_dotenv



# Functions for agents here
def execute_query(query):
    """
    Executes a provided query in the database and returns the results
    """
    load_dotenv()
    db_pass = os.getenv("DB_PASSWORD")
    host = os.getenv("HOST")

    with pg.connect(f'dbname=postgres user=postgres host={host} port=5432 password={db_pass}') as conn:
        with conn.cursor() as cur:
            cur.execute(query)

            query_results = cur.fetchall()
            return query_results 

def calc_posterior(likelihood, prior, evidence):
    """
    Calculates the posterior probability using Bayes' rule given a likelihood, a prior, and some evidence.
    """
    if evidence == 0: 
        return "Cannot have probabilities that are equal to 0"
    else:
        return (likelihood * prior) / evidence 

def get_news(query, method):
    """
    Get the news for a specific related event or question.
    @param: query - the news event, in the form of a sentence or keyword, to get news for.
    @param: method - which method to use in the search, has to be either "nl" for natural language or "kw" for keyword search.
    @returns: a list of dicts with news related to the query from the past 48 hours.
    """
    ask = AskNewsSDK()
    
    response = ask.news.search_news(
        query=query, 
        n_articles=10,
        return_type='string',
        method=method,
    )

    return response.as_string

# agents
main_agent = Agent(
    name = "Main agent", 
    description = "",
)

query_agent = Agent(
    name = "Query agent", 
    description = "",
    functions = execute_query, 
)

news_agent = Agent(
    name = "News agent",
    description = "", 
    functions = get_news,
)

bayes_agent = Agent(
    name = "Bayes agent", 
    description = "", 
    functions = calc_posterior,
)


