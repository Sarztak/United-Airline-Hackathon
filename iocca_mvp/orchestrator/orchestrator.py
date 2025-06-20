import pandas as pd

class Orchestrator:
    def __init__(self, crew_agent, ops_agent, policy_agent):
        self.crew_agent = crew_agent
        self.ops_agent = ops_agent
        self.policy_agent = policy_agent

    def handle_disruption(self, crew_roster, flight_schedule, hotel_inventory, reposition_flights, duty_rules):
        crew_df = pd.DataFrame(crew_roster)
        flight_df = pd.DataFrame(flight_schedule)
        hotel_df = pd.DataFrame(hotel_inventory)
        reposition_df = pd.DataFrame(reposition_flights)

        results = {"steps": []}

        # Crew Assignment
        crew_result = self.crew_agent(
            flight_id=flight_schedule[0]["flight_id"],
            crew_roster_df=crew_df,
            flight_schedule_df=flight_df,
            repositioning_flights_df=reposition_df,
            duty_rules=duty_rules
        )
        results["steps"].append({"crew_assignment": crew_result})

        if crew_result.get("policy"):
            results["steps"].append({"crew_policy": crew_result["policy"]})

        if crew_result["status"] == "escalation_required":
            llm_result = self.policy_agent(
                query=crew_result["message"],
                context={"crew_result": crew_result}
            )
            results["steps"].append({"llm_policy": llm_result})
            results["final_status"] = llm_result["llm_decision"]
            return results

        if crew_result["status"] in ["reassigned", "repositioning_initiated"]:
            crew_id = crew_result.get("spare_used")
            origin = flight_df.loc[flight_df["flight_id"] == flight_schedule[0]["flight_id"], "origin"].iloc[0]
            ops_result = self.ops_agent(crew_id, origin, hotel_df)
            results["steps"].append({"ops_support": ops_result})

            if ops_result.get("policy"):
                results["steps"].append({"ops_policy": ops_result["policy"]})

            if ops_result["status"] == "escalation_required":
                llm_result = self.policy_agent(
                    query=ops_result["message"],
                    context={"ops_result": ops_result}
                )
                results["steps"].append({"llm_policy": llm_result})
                results["final_status"] = llm_result["llm_decision"]
                return results

        results["final_status"] = crew_result["status"]
        return results 