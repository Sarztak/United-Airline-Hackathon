from dotenv import load_dotenv
from langchain.agents import initialize_agent, Tool, AgentType
from tools import StatusQueryTools
from mock_data import crew_roster_df, repositioning_flights_df, flight_schedule_df, hotels_df, transport_df, policies_df
from debug_llm import DebugLLMWrapper
from helper import load_llm
from prompt_templates import build_final_prompt, crew_disruption_prompt_v1



if __name__ == "__main__":
    load_dotenv()
    llm = load_llm(service="openai", model="gpt-4o-mini")


    status_query_tools = StatusQueryTools(
        crew_roster_df=crew_roster_df,
        flight_schedule_df=flight_schedule_df,
        repositioning_flights_df=repositioning_flights_df,
        hotels_df = hotels_df,
        transport_df=transport_df,
        policies_df=policies_df
    )

    agent = initialize_agent(
        status_query_tools.tools, 
        llm, 
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )

    # print(agent.input_keys) for debugging

    for _, row in flight_schedule_df.iterrows():
        current_flight_data = (
            f"Flight ID: {row['flight_id']}\n"
            f"Status: {row['status']}\n"
            f"Delay minutes: {row['delay_minutes']}\n"
            f"Gate: {row['gate']}\n"
            f"Remarks: {row['remarks']}\n"
            f"Aircraft type: {row['aircraft_type']}"
        )

    entry_prompt = build_final_prompt(
        current_flight_data=current_flight_data, 
        report_buffer=60
    )


    agent = initialize_agent(
        tools=status_query_tools.tools,
        llm=llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True
    )

    result = agent.invoke(entry_prompt)











