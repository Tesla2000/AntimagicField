from __future__ import annotations

from datetime import datetime
from typing import Literal
from typing import Optional
from typing import TYPE_CHECKING

import cachetools.func
from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage
from modules.action_plan_step import ActionPlanStep
from prompts.emergency_fund import ACTION_PLAN_PROMPT
from prompts.emergency_fund import EMERGENCY_FUND_ASSESSMENT
from prompts.emergency_fund import EMERGENCY_FUND_DISABILITY_INSURANCE
from prompts.emergency_fund import EMERGENCY_FUND_INSURANCE_ANALYSIS
from prompts.emergency_fund import EMERGENCY_FUND_INSURANCE_STATUS
from prompts.emergency_fund import EMERGENCY_FUND_MARKET_ANALYSIS
from prompts.emergency_fund import EMERGENCY_FUND_SAVINGS_ACCOUNTS
from prompts.emergency_fund import HIGH_YIELD_ACCOUNTS_PROMPT
from prompts.emergency_fund import SHORT_TERM_DISABILITY_INSURANCE_PROMPT
from utils.model_manager import ModelManager

from consts import GOOD_MODELS
from consts import LONG_CONTEXT
from consts import MAX_ITERATIONS_WITHOUT_COMPLETION

if TYPE_CHECKING:
    from state import State


class EmergencyFund(ActionPlanStep):
    walkthrough_step: Optional[
        Literal[
            "emergency_fund_assessment",
            "emergency_fund_analysis",
            "emergency_fund_insurance_status",
            "emergency_fund_progress_tracking",
        ]
    ] = None

    async def _handle_emergency_fund_assessment(
        self, state: "State"
    ) -> Optional["State"]:
        plaid_data = state.context.plaid_data
        calculation_results = (
            state.context.action_plan_state.calculation_results
        )
        monthly_expenses = plaid_data.get_monthly_expenses()
        emergency_fund_balance = plaid_data.get_emergency_fund_balance()
        savings_rate = plaid_data.calculate_savings_rate()

        calculation_results["emergency_fund"] = {
            "balance": emergency_fund_balance,
            "monthly_expenses": monthly_expenses,
            "months_covered": (
                emergency_fund_balance / monthly_expenses
                if monthly_expenses > 0
                else 0
            ),
            "savings_rate": savings_rate,
        }
        if result := self._respond(
            state,
            EMERGENCY_FUND_ASSESSMENT,
        ):
            return result
        self.walkthrough_step = "emergency_fund_analysis"

    async def _handle_emergency_fund_analysis(
        self, state: "State"
    ) -> Optional["State"]:
        plaid_data = state.context.plaid_data
        savings_accounts = plaid_data.saving_accounts

        market_analysis = analyse_market()
        account_info = "\n".join(
            f"- {a.name}: ${a.balances.current:,.2f}" for a in savings_accounts
        )
        if result := self._respond(
            state,
            EMERGENCY_FUND_SAVINGS_ACCOUNTS.format(
                account_info=account_info, market_analysis=market_analysis
            ),
        ):
            return result
        self.walkthrough_step = "emergency_fund_insurance_status"

    async def _handle_emergency_fund_insurance_status(
        self, state: "State"
    ) -> Optional["State"]:
        plaid_data = state.context.plaid_data
        calculation_results = (
            state.context.action_plan_state.calculation_results
        )
        emergency_fund = calculation_results["emergency_fund"]

        if "timeline_projections" not in calculation_results["emergency_fund"]:
            monthly_savings = emergency_fund["savings_rate"][
                "savings_deposits"
            ]
            target_3_months = emergency_fund["monthly_expenses"] * 3
            target_6_months = emergency_fund["monthly_expenses"] * 6
            current_balance = emergency_fund["balance"]

            months_to_3_months = (
                (target_3_months - current_balance) / monthly_savings
                if monthly_savings > 0
                else float("inf")
            )
            months_to_6_months = (
                (target_6_months - current_balance) / monthly_savings
                if monthly_savings > 0
                else float("inf")
            )

            calculation_results["emergency_fund"]["timeline_projections"] = {
                "target_3_months": target_3_months,
                "target_6_months": target_6_months,
                "months_to_3_months": months_to_3_months,
                "months_to_6_months": months_to_6_months,
                "monthly_savings": monthly_savings,
            }

        timeline = emergency_fund["timeline_projections"]

        credit_utilization = plaid_data.calculate_credit_utilization()
        discretionary_ratio = (
            plaid_data.calculate_discretionary_spending_ratio()
        )

        lacks_coverage = ModelManager(
            models=GOOD_MODELS
        ).invoke_model_with_structured_output(
            EMERGENCY_FUND_INSURANCE_STATUS,
            state.messages,
            bool,
            1,
        )

        if lacks_coverage:
            insurance_analysis_response = analyse_insurance()

            calculation_results["emergency_fund"]["insurance_research"] = {
                "type": "short_term_disability",
                "market_analysis": insurance_analysis_response.content,
                "last_updated": datetime.now().isoformat(),
            }
        else:
            insurance_analysis_response = AIMessage(content="")
        if result := self._respond(
            state,
            EMERGENCY_FUND_DISABILITY_INSURANCE.format(
                emergency_fund_balance=float(emergency_fund["balance"]),
                emergency_fund_expenses=float(
                    emergency_fund["monthly_expenses"]
                ),
                emergency_fund_savings_rate=float(
                    emergency_fund["savings_rate"]["rate"]
                ),
                target_3_months=float(timeline["target_3_months"]),
                months_to_3_months=float(timeline["months_to_3_months"]),
                target_6_months=float(timeline["target_6_months"]),
                months_to_6_months=float(timeline["months_to_6_months"]),
                overall_utilization=float(
                    credit_utilization["overall_utilization"]
                ),
                discretionary_ratio=float(discretionary_ratio["ratio"]),
                insurance_analysis_response=insurance_analysis_response.content,
            ),
        ):
            return result

        self.walkthrough_step = "emergency_fund_progress_tracking"

    async def _handle_emergency_fund_progress_tracking(
        self, state: "State"
    ) -> Optional["State"]:
        calculation_results = (
            state.context.action_plan_state.calculation_results
        )
        emergency_fund = calculation_results["emergency_fund"]

        timeline = calculation_results["emergency_fund"][
            "timeline_projections"
        ]
        tracking_milestones = [
            {
                "target": "1_month",
                "amount": emergency_fund["monthly_expenses"],
                "progress": min(
                    100,
                    (
                        emergency_fund["balance"]
                        / emergency_fund["monthly_expenses"]
                    )
                    * 100,
                ),
                "remaining": max(
                    0,
                    emergency_fund["monthly_expenses"]
                    - emergency_fund["balance"],
                ),
            },
            {
                "target": "3_months",
                "amount": timeline["target_3_months"],
                "progress": min(
                    100,
                    (emergency_fund["balance"] / timeline["target_3_months"])
                    * 100,
                ),
                "remaining": max(
                    0, timeline["target_3_months"] - emergency_fund["balance"]
                ),
            },
            {
                "target": "6_months",
                "amount": timeline["target_6_months"],
                "progress": min(
                    100,
                    (emergency_fund["balance"] / timeline["target_6_months"])
                    * 100,
                ),
                "remaining": max(
                    0, timeline["target_6_months"] - emergency_fund["balance"]
                ),
            },
        ]

        progress_text = "\n".join(
            [
                f"{'✓' if m['progress'] >= 100 else '○'} {m['target']}: {m['progress']:.1f}% complete (${'{0:,.2f}'.format(m['remaining'])} remaining)"
                for m in tracking_milestones
            ]
        )
        final_response = await ModelManager(
            models=GOOD_MODELS
        ).generate_response(
            ACTION_PLAN_PROMPT.format(progress_text=progress_text),
            state.messages,
            1,
        )
        self.walkthrough_completion = 1
        return state.updated_state(
            messages=[final_response],
            phase="action_plan",
        )

    async def execute(self, state: "State") -> "State":
        f"""Handles walkthrough steps. When walkthrough step passes the
        response to another step is doesn't return value and a handler
        corresponding to the step is user up to
        {MAX_ITERATIONS_WITHOUT_COMPLETION} times.
        After that it is considered an infinite loop"""
        for _ in range(MAX_ITERATIONS_WITHOUT_COMPLETION):
            match self.walkthrough_step:
                case None:
                    handler = self._handle_emergency_fund_assessment
                case "emergency_fund_assessment":
                    handler = self._handle_emergency_fund_assessment
                case "emergency_fund_analysis":
                    handler = self._handle_emergency_fund_analysis
                case "emergency_fund_insurance_status":
                    handler = self._handle_emergency_fund_insurance_status
                case "emergency_fund_progress_tracking":
                    handler = self._handle_emergency_fund_progress_tracking
                case _:
                    raise ValueError(
                        f"Unknown walkthrough step: {self.walkthrough_step}"
                    )
            result = await handler(state)
            if result:
                return result
        raise ValueError("No results returned, infinite loop")

    @staticmethod
    def _respond(state: "State", prompt: str) -> Optional["State"]:
        response = ModelManager(
            tool_models=GOOD_MODELS
        ).invoke_model_with_structured_output(
            prompt,
            state.messages,
            Optional[str],
            LONG_CONTEXT,
        )
        if response and response != "None":
            return state.updated_state(messages=[AIMessage(response)])


@cachetools.func.ttl_cache(ttl=24 * 60 * 60)  # until redis is implemented
def analyse_market():
    web_response = ModelManager().generate_web_agent_response(
        [HumanMessage(content=HIGH_YIELD_ACCOUNTS_PROMPT)]
    )

    return ModelManager(models=GOOD_MODELS).generate_response_no_stream(
        EMERGENCY_FUND_MARKET_ANALYSIS.format(web_response.content), []
    )


@cachetools.func.ttl_cache(ttl=24 * 60 * 60)  # until redis is implemented
def analyse_insurance():
    web_response = ModelManager().generate_web_agent_response(
        [HumanMessage(content=SHORT_TERM_DISABILITY_INSURANCE_PROMPT)]
    )
    return ModelManager(models=GOOD_MODELS).generate_response_no_stream(
        EMERGENCY_FUND_INSURANCE_ANALYSIS.format(web_response.content),
        [],
    )
