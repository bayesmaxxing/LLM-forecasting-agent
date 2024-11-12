from asknews_sdk import AskNewsSDK
from openai import OpenAI
from swarm import Agent, Swarm
import psycopg as pg 
import os 
from dotenv import load_dotenv
from typing import AsyncGenerator
import asyncio
import contextlib

class ForecastSwarm:
    def __init__(self):
        load_dotenv()
        self.client = Swarm()
        self.db_schema = """Table: forecast_v2, fields:[id : unique integer for each forecast, question: string with the forecast question, category: string with one or more categories the forecast belongs to,
            created: datetime of question creation, resolution_criteria: string with information about the conditions for the forecast to resolve as  Yes or No, 
            resolution: string with information about how the forecast resolved. Is equal to "0" if the forecast did not happen, "1" is it happened and "-" if it resolved as ambiguous, 
            resolved: datetime of question resolution, brier_score: Brier score obtained from the forecast, log2_score: the Log score in base 2 obtained for the forecast,
            logn_score: the Log score in natural logarithm obtained for the forecast, comment: string comment from the user on the resolution], 
            Table: forecast_points, fields:[update_id: unique integer for the forecast point, forecast_id: the unique integer for each forecast, point_forecast: the forecasted probability as a float, 
            upper_ci: the upper confidence interval on the forecasted probability, lower_ci: the lower confidence interval on the forecasted probability, 
            reason: a string with the user's reason for the forecast point, created: datetime of forecast point creation]
            """
        self.setup_agents()

    def setup_agents(self):
        self.main_agent = Agent(
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
            functions = [self.transfer_to_bayes, self.transfer_to_query, self.transfer_to_news],
        ) 

        self.query_agent = Agent(
            name = "Query agent", 
            instruction = f"""You are to answer the user's question about their forecasts, forecast points, or aggregate statistics truthfully. To your help, you have the
            user's database. To use the database, write a query that gives you information the information that you need and pass it to the execute_query function.
            The database has the following structure {self.db_schema}.
            If you feel like the information you've got is not enough, transfer back to Main agent to obtain more information.
            """,
            functions = [self.execute_query, self.transfer_to_main],
        )

        self.bayes_agent = Agent(
            name = "Bayes agent", 
            instruction = f"""You are to determine the user's likelihood, evidence, and prior from their request and use that for the calc_posterior function
            to help the user determine an appropriate forecast update.
            If you are unable to parse the user's likelihood, evidence and prior, transfer back to Main agent to obtain more information.
            """, 
            functions = [self.calc_posterior,self.transfer_to_main],
        )

        self.news_agent = Agent(
            name = "News agent",
            instruction = f"""You are to determine what news the user is interested in finding. Based on that understanding, you'll create a 
            query to pass to the get_news function. If you feel like the information you've got is not enough to perform the news search, transfer back to Main agent to obtain more information.
            """, 
            functions = [self.get_news, self.transfer_to_main],
        )

    def execute_query(self, query: str):
        """
        Executes a provided query in the database and returns the results asynchronously
        """
        load_dotenv()
        db_pass = os.getenv("DB_PASSWORD")
        host = os.getenv("HOST")

        with pg.connect(
            f'dbname=postgres user=postgres host={host} port=5432 password={db_pass}'
        ) as conn:
             with conn.cursor() as cur:
                cur.execute(query)
                query_results = cur.fetchall()
                return query_results

    def get_news(self, query: str):
        """
        Get the news for a specific related event or question asynchronously
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
            method="nl"
        )

        return response.as_string

    def calc_posterior(self, likelihood: float, prior: float, evidence: float):
        if evidence == 0: 
            return "Cannot have probabilities that are equal to 0"
        else:
            return (likelihood * prior) / evidence 

    def transfer_to_main(self):
        return self.main_agent
    
    def transfer_to_news(self):
        return self.news_agent 
    
    def transfer_to_bayes(self):
        return self.bayes_agent 

    def transfer_to_query(self):
        return self.query_agent 

    async def stream_run(self, message: str) -> AsyncGenerator[str, None]:
        """
        Async generator that streams the response chunks
        """
        response = self.client.run(
            agent=self.main_agent,
            messages=[{"role": "user", "content": message}],
            stream=True
        )

        for chunk in response:
            if chunk and chunk.get('content') is not None:
                yield chunk.get('content')
                await asyncio.sleep(0.01)

if __name__ == "__main__":
    async def main():
        swarm = ForecastSwarm()
        async for chunk in swarm.stream_run("Hey, what's the latest news on the US Federal Reserve and the FED funds rate?"):
            print(chunk, end="", flush=True)

    asyncio.run(main())                
