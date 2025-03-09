import sys
import json
import logging
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from colorama import Fore, Style, init
import questionary

from agents.portfolio_manager import portfolio_management_agent
from agents.risk_manager import risk_management_agent
from graph.state import AgentState
from utils.display import print_trading_output
from utils.analysts import ANALYST_ORDER, get_analyst_nodes
from utils.progress import progress
from llm.models import LLM_ORDER, get_model_info

import argparse
from datetime import datetime
from dateutil.relativedelta import relativedelta
from utils.visualize import save_graph_as_png


# Set the logging level based on an environment variable
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
#LOG_LEVEL = logging.DEBUG

logging.basicConfig(
    #level=LOG_LEVEL,
    level=logging.DEBUG,
    #format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s"
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
)

# silence font thing
logging.getLogger('matplotlib').setLevel(logging.WARNING)
#logging.getLogger('matplotlib').disabled = True
# Suppress debug logs from PIL (Pillow)
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("openai._base_client").setLevel(logging.WARNING)
logging.getLogger("httpcore.http11").setLevel(logging.WARNING)
logging.getLogger("httpcore.connection").setLevel(logging.WARNING)

# Create a logger with a specific name
logger = logging.getLogger(__name__)

logger.info("Main started")

# Create a console handler with formatting
console_handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s [%(name)s] [%(levelname)s] %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


# Debug before loading the .env file
logger.debug("Before load_dotenv: USE_IBKR = %r", os.environ.get("USE_IBKR"))
logger.debug("Current working directory: %s", os.getcwd())
# Load environment variables from .env file
# dotenv_path='/path/to/your/.env')
load_dotenv(os.getcwd()+'/.env')

# Debug after loading the .env file
logger.debug("After load_dotenv: USE_IBKR = %r", os.environ.get("USE_IBKR"))


init(autoreset=True)


def parse_hedge_fund_response(response):
    import json

    try:
        return json.loads(response)

    except json.JSONDecodeError:
        print(f"Error parsing response: {response}")
        return None

##### Run the Hedge Fund #####
def run_hedge_fund(
    tickers: list[str],
    start_date: str,
    end_date: str,
    portfolio: dict,
    show_reasoning: bool = False,
    selected_analysts: list[str] = [],
    model_name: str = "gpt-4o",
    model_provider: str = "OpenAI",
):
    # Start progress tracking
    progress.start()

    try:
        # Create a new workflow if analysts are customized
        if selected_analysts:
            workflow = create_workflow(selected_analysts)
            agent = workflow.compile()
        else:
            agent = app

        final_state = agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="Make trading decisions based on the provided data.",
                    )
                ],
                "data": {
                    "tickers": tickers,
                    "portfolio": portfolio,
                    "start_date": start_date,
                    "end_date": end_date,
                    "analyst_signals": {},
                },
                "metadata": {
                    "show_reasoning": show_reasoning,
                    "model_name": model_name,
                    "model_provider": model_provider,
                },
            },
        )

        return {
            "decisions": parse_hedge_fund_response(final_state["messages"][-1].content),
            "analyst_signals": final_state["data"]["analyst_signals"],
        }
    finally:
        # Stop progress tracking
        progress.stop()


def start(state: AgentState):
    """Initialize the workflow with the input message."""
    return state


def create_workflow(selected_analysts=None):
    """Create the workflow with selected analysts."""
    workflow = StateGraph(AgentState)
    workflow.add_node("start_node", start)

    # Get analyst nodes from the configuration
    analyst_nodes = get_analyst_nodes()

    # Default to all analysts if none selected
    if selected_analysts is None:
        selected_analysts = list(analyst_nodes.keys())

    # Add selected analyst nodes
    for analyst_key in selected_analysts:
        node_name, node_func = analyst_nodes[analyst_key]
        workflow.add_node(node_name, node_func)
        workflow.add_edge("start_node", node_name)

    # Always add risk and portfolio management
    workflow.add_node("risk_management_agent", risk_management_agent)
    workflow.add_node("portfolio_management_agent", portfolio_management_agent)

    # Connect selected analysts to risk management
    for analyst_key in selected_analysts:
        node_name = analyst_nodes[analyst_key][0]
        workflow.add_edge(node_name, "risk_management_agent")

    workflow.add_edge("risk_management_agent", "portfolio_management_agent")
    workflow.add_edge("portfolio_management_agent", END)

    workflow.set_entry_point("start_node")
    return workflow


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the hedge fund trading system")
    parser.add_argument(
        "--initial-cash",
        type=float,
        default=15000.0,
        help="Initial cash position. Defaults to 100000.0)"
    )
    parser.add_argument(
        "--margin-requirement",
        type=float,
        default=20.0,
        help="Initial margin requirement. Defaults to 0.0"
    )
    parser.add_argument("--tickers", type=str, required=True, help="Comma-separated list of stock ticker symbols")
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date (YYYY-MM-DD). Defaults to 3 months before end date",
    )
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD). Defaults to today")
    parser.add_argument("--show-reasoning", action="store_true", help="Show reasoning from each agent")
    parser.add_argument(
        "--show-agent-graph", action="store_true", help="Show the agent graph"
    )
    parser.add_argument(
        "--analysts", 
        type=str,
        help="Comma-separated list of analysts (e.g., 'technical_analyst,fundamentals_analyst')"
    )
    parser.add_argument(
        "--model",
        type=str,
        help="LLM model name (e.g., 'gpt-4')"
    )
    parser.add_argument(
        "--model-provider",
        type=str,
        help="Model provider (e.g., 'OpenAI')"
    )
    parser.add_argument(
        "--initial-positions",
        type=str,
        help="JSON string of initial positions (e.g., '{\"AAPL\": {\"long\": 100, \"short\": 0, \"long_cost_basis\": 150.0, \"short_cost_basis\": 0.0}}')"
    )

    args = parser.parse_args()

    # Parse tickers from comma-separated string
    tickers = [ticker.strip() for ticker in args.tickers.split(",")]

    # Handle analysts selection
    selected_analysts = None
    if args.analysts:
        if args.analysts.lower() == "all":
            selected_analysts = [value for _, value in ANALYST_ORDER]
            print(f"\nSelected all analysts: {', '.join(Fore.GREEN + analyst.title().replace('_', ' ') + Style.RESET_ALL for analyst in selected_analysts)}\n")
        else:
            selected_analysts = [analyst.strip() for analyst in args.analysts.split(",")]
            # Validate analysts
            valid_analysts = [value for _, value in ANALYST_ORDER]
            invalid_analysts = [a for a in selected_analysts if a not in valid_analysts]
            if invalid_analysts:
                print(f"{Fore.RED}Invalid analysts: {', '.join(invalid_analysts)}")
                print(f"Valid options are: 'all' or {', '.join(valid_analysts)}{Style.RESET_ALL}")
                sys.exit(1)
            print(f"\nSelected analysts: {', '.join(Fore.GREEN + analyst.title().replace('_', ' ') + Style.RESET_ALL for analyst in selected_analysts)}\n")
    else:
        choices = questionary.checkbox(
            "Select your AI analysts.",
            choices=[questionary.Choice(display, value=value) for display, value in ANALYST_ORDER],
            instruction="\n\nInstructions: \n1. Press Space to select/unselect analysts.\n2. Press 'a' to select/unselect all.\n3. Press Enter when done to run the hedge fund.\n",
            validate=lambda x: len(x) > 0 or "You must select at least one analyst.",
            style=questionary.Style(
                [
                    ("checkbox-selected", "fg:green"),
                    ("selected", "fg:green noinherit"),
                    ("highlighted", "noinherit"),
                    ("pointer", "noinherit"),
                ]
            ),
        ).ask()
        if not choices:
            print("\n\nInterrupt received. Exiting...")
            sys.exit(0)
        selected_analysts = choices
        print(f"\nSelected analysts: {', '.join(Fore.GREEN + choice.title().replace('_', ' ') + Style.RESET_ALL for choice in choices)}\n")

    # Handle model selection
    model_choice = args.model
    model_provider = args.model_provider
    if model_choice and model_provider:
        print(f"\nSelected {Fore.CYAN}{model_provider}{Style.RESET_ALL} model: {Fore.GREEN + Style.BRIGHT}{model_choice}{Style.RESET_ALL}\n")
    else:
        model_choice = questionary.select(
            "Select your LLM model:",
            choices=[questionary.Choice(display, value=value) for display, value, _ in LLM_ORDER],
            style=questionary.Style([
                ("selected", "fg:green bold"),
                ("pointer", "fg:green bold"),
                ("highlighted", "fg:green"),
                ("answer", "fg:green bold"),
            ])
        ).ask()

        if not model_choice:
            print("\n\nInterrupt received. Exiting...")
            sys.exit(0)
        else:
            # Get model info using the helper function
            model_info = get_model_info(model_choice)
            if model_info:
                model_provider = model_info.provider.value
                print(f"\nSelected {Fore.CYAN}{model_provider}{Style.RESET_ALL} model: {Fore.GREEN + Style.BRIGHT}{model_choice}{Style.RESET_ALL}\n")
            else:
                model_provider = "Unknown"
                print(f"\nSelected model: {Fore.GREEN + Style.BRIGHT}{model_choice}{Style.RESET_ALL}\n")

    # Create the workflow with selected analysts
    workflow = create_workflow(selected_analysts)
    app = workflow.compile()

    if args.show_agent_graph:
        file_path = ""
        if selected_analysts is not None:
            for selected_analyst in selected_analysts:
                file_path += selected_analyst + "_"
            file_path += "graph.png"
        save_graph_as_png(app, file_path)

    # Validate dates if provided
    if args.start_date:
        try:
            datetime.strptime(args.start_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Start date must be in YYYY-MM-DD format")

    if args.end_date:
        try:
            datetime.strptime(args.end_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("End date must be in YYYY-MM-DD format")

    # Set the start and end dates
    end_date = args.end_date or datetime.now().strftime("%Y-%m-%d")
    if not args.start_date:
        # Calculate 3 months before end_date
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        start_date = (end_date_obj - relativedelta(months=1)).strftime("%Y-%m-%d")
    else:
        start_date = args.start_date

    # Initialize portfolio with cash amount and stock positions
    portfolio = {
        "cash": args.initial_cash,  # Initial cash amount
        "margin_requirement": args.margin_requirement,  # Initial margin requirement
        "positions": {
            ticker: {
                "long": 0,  # Number of shares held long
                "short": 0,  # Number of shares held short
                "long_cost_basis": 0.0,  # Average cost basis for long positions
                "short_cost_basis": 0.0,  # Average price at which shares were sold short
            } for ticker in tickers
        },
        "realized_gains": {
            ticker: {
                "long": 0.0,  # Realized gains from long positions
                "short": 0.0,  # Realized gains from short positions
            } for ticker in tickers
        }
    }

    #logger.debug("Portfolio1= %r", portfolio )
#    try:
#        # Factory returns IBKRClientWrapper or FinancialsAPIClient based on USE_IBKR
#        client = get_api_client()
#        # If using legacy financials client:
#        porto = client.get_portfolio()
#        #port = client.portfolio_to_df(portfolio)
#
#    except NotImplementedError:
#        # In case IBKR client is chosen but get_financial_metrics is not supported:
#        print("get_portfolio is not implemented for this API client.")
#        portfolio = {
#            "cash": args.initial_cash,  # Initial cash amount
#            "positions": {ticker: 0 for ticker in tickers}  # Initial stock positions
#        }
    #logger.debug("Portfolio2= %r", porto )
    logger.debug("Portfolio3= %r", portfolio )

    # Update portfolio with initial positions if provided
    if args.initial_positions:
        try:
            initial_positions = json.loads(args.initial_positions)
            for ticker, position in initial_positions.items():
                if ticker in portfolio["positions"]:
                    portfolio["positions"][ticker].update(position)
                else:
                    print(f"{Fore.YELLOW}Warning: Position provided for unknown ticker {ticker}{Style.RESET_ALL}")
        except json.JSONDecodeError:
            print(f"{Fore.RED}Error: Invalid JSON format for initial positions{Style.RESET_ALL}")
            sys.exit(1)

    # Run the hedge fund
    result = run_hedge_fund(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        portfolio=portfolio,
        show_reasoning=args.show_reasoning,
        selected_analysts=selected_analysts,
        model_name=model_choice,
        model_provider=model_provider,
    )
    print_trading_output(result)
