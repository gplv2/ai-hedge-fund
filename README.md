# AI Hedge Fund

This is a proof of concept for an AI-powered hedge fund. The goal of this project is to explore the use of AI to make trading decisions. This project is for **educational** purposes only and is not intended for real trading or investment.

This system employs several agents working together:

1. Ben Graham Agent - The godfather of value investing, only buys hidden gems with a margin of safety
2. Bill Ackman Agent - An activist investors, takes bold positions and pushes for change
3. Cathie Wood Agent - The queen of growth investing, believes in the power of innovation and disruption
4. Charlie Munger Agent - Warren Buffett's partner, only buys wonderful businesses at fair prices
5. Stanley Druckenmiller Agent - Macro trading legend who hunts for asymmetric opportunities with explosive growth potential
6. Warren Buffett Agent - The oracle of Omaha, seeks wonderful companies at a fair price
7. Valuation Agent - Calculates the intrinsic value of a stock and generates trading signals
8. Sentiment Agent - Analyzes market sentiment and generates trading signals
9. Fundamentals Agent - Analyzes fundamental data and generates trading signals
10. Technicals Agent - Analyzes technical indicators and generates trading signals
11. Risk Manager - Calculates risk metrics and sets position limits
12. Portfolio Manager - Makes final trading decisions and generates orders

<img width="1020" alt="Screenshot 2025-03-08 at 4 45 22 PM" src="https://github.com/user-attachments/assets/d8ab891e-a083-4fed-b514-ccc9322a3e57" />

**Note**: the system simulates trading decisions, it does not actually trade.

[![Twitter Follow](https://img.shields.io/twitter/follow/virattt?style=social)](https://twitter.com/virattt)

## Disclaimer

This project is for **educational and research purposes only**.

- Not intended for real trading or investment
- No warranties or guarantees provided
- Past performance does not indicate future results
- Creator assumes no liability for financial losses
- Consult a financial advisor for investment decisions

By using this software, you agree to use it solely for learning purposes.

## Table of Contents

- [Setup](#setup)
- [Usage](#usage)
  - [Running the Hedge Fund](#running-the-hedge-fund)
  - [Running the Backtester](#running-the-backtester)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [Feature Requests](#feature-requests)
- [License](#license)

## This mod depends on the IBEAM IBKR webgateway or all the other alternative solutions.

If you want to play with Interactive brokers, You'll need Docker, you'll also need an IBKR account.  But the standard Financials ai is still supported.  Via my broker I have access to all tickers I want, I cannot afford extra 200+ per month for market data.  So I want to combine API's .  It also seems like a good idea to not pull all information from 1 source.

see the ibeam submodule on how to set it up, I found this to be one of the best Docker solutions available, and with some elbow grease you'll get SSL sorted out too with certs.  That's what the outputs directory is for.

I redesigned the cache system as it was not transparant enough.  It is much easier to make a wrapper.  I chose redis but extending this system now is piece of cake without even working in other files.

My own goal is to get a bunch of API's together to figure out the best and compare data.  The Backtester is also maintained.  I'm not sure what to do yet with this project, I have some doubts on hpw the calls work, some strange API behavior from Financials.  Also , the portofolio proved to be underdeveloped, I haven't tackled this too much but I hooked my wallet up, and thought that would be enough but it seemed to disregard what I had.   I've got a few more idea's to implement.

On terms of logic, I'm not convinved that sentimentals make a huge difference and should have the weight it has.

it needs:

 - Redis server
 - ibeam
 - (ibind but that should be installed by uv ), the submodule here is for dev purposes

## Setup

Clone the repository:

```bash
git clone --recurse-submodules https://github.com/virattt/ai-hedge-fund.git
```

Take care of the submodules
```bash
cd ai-hedge-fund
git submodule update --init --recursive
git submodule status
```

1. Install uv (if not already installed):
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

2. Install dependencies:

```bash
# Install dependencies from pyproject.toml
uv sync
```

3. Set up your environment variables:

```bash
# Create .env file for your API keys
cp .env.example .env
```

4. Set your API keys:

```bash
# For running LLMs hosted by openai (gpt-4o, gpt-4o-mini, etc.)
# Get your OpenAI API key from https://platform.openai.com/
OPENAI_API_KEY=your-openai-api-key

# For running LLMs hosted by groq (deepseek, llama3, etc.)
# Get your Groq API key from https://groq.com/
GROQ_API_KEY=your-groq-api-key

# For getting financial data to power the hedge fund
# Get your Financial Datasets API key from https://financialdatasets.ai/
FINANCIAL_DATASETS_API_KEY=your-financial-datasets-api-key
```

**Important**: You must set `OPENAI_API_KEY`, `GROQ_API_KEY`, or `ANTHROPIC_API_KEY` for the hedge fund to work. If you want to use LLMs from all providers, you will need to set all API keys.

Financial data for AAPL, GOOGL, MSFT, NVDA, and TSLA is free and does not require an API key.

For any other ticker, you will need to set the `FINANCIAL_DATASETS_API_KEY` in the .env file.

## Usage

### CLI Arguments

The hedge fund supports the following command line arguments:

| Argument               | Description                                                           | Default                  | Example                                                                                                |
| ---------------------- | --------------------------------------------------------------------- | ------------------------ | ------------------------------------------------------------------------------------------------------ |
| `--tickers`            | Comma-separated list of stock ticker symbols                          | Required                 | `--tickers AAPL,MSFT,NVDA`                                                                             |
| `--analysts`           | Comma-separated list of analysts to use (skips interactive selection) | Interactive prompt       | `--analysts all` or `--analysts technical_analyst,fundamentals_analyst`                                |
| `--model`              | LLM model name (skips interactive selection)                          | Interactive prompt       | `--model gpt-4`                                                                                        |
| `--model-provider`     | Model provider (skips interactive selection)                          | Interactive prompt       | `--model-provider OpenAI`                                                                              |
| `--initial-cash`       | Initial cash position                                                 | 100000.0                 | `--initial-cash 500000`                                                                                |
| `--initial-positions`  | JSON string of initial positions                                      | Empty positions          | `--initial-positions '{"AAPL":{"long":100,"short":0,"long_cost_basis":150.0,"short_cost_basis":0.0}}'` |
| `--margin-requirement` | Initial margin requirement                                            | 0.0                      | `--margin-requirement 0.5`                                                                             |
| `--start-date`         | Start date in YYYY-MM-DD format                                       | 3 months before end date | `--start-date 2024-01-01`                                                                              |
| `--end-date`           | End date in YYYY-MM-DD format                                         | Today                    | `--end-date 2024-03-01`                                                                                |
| `--show-reasoning`     | Show reasoning from each agent                                        | False                    | `--show-reasoning`                                                                                     |
| `--show-agent-graph`   | Generate a visualization of the agent workflow                        | False                    | `--show-agent-graph`                                                                                   |

Available analysts:

- Use `--analysts all` to select all analysts, or specify individual analysts:
  - `technical_analyst`: Technical analysis
  - `fundamentals_analyst`: Fundamental analysis
  - `sentiment_analyst`: Sentiment analysis
  - `valuation_analyst`: Valuation analysis
  - `warren_buffett`: Warren Buffett's principles
  - `bill_ackman`: Bill Ackman's principles

Available model providers:

- `OpenAI`: Requires OPENAI_API_KEY
- `Groq`: Requires GROQ_API_KEY
- `Anthropic`: Requires ANTHROPIC_API_KEY

Available models by provider:

OpenAI models:

- `gpt-4o`: GPT-4 Optimized
- `gpt-4o-mini`: GPT-4 Mini Optimized
- `o1`: OpenAI One
- `o3-mini`: OpenAI Three Mini

Groq models:

- `deepseek-r1-distill-llama-70b`: DeepSeek R1 70B
- `llama-3.3-70b-versatile`: Llama 3.3 70B

Anthropic models:

- `claude-3-5-haiku-latest`: Claude 3.5 Haiku
- `claude-3-5-sonnet-latest`: Claude 3.5 Sonnet
- `claude-3-opus-latest`: Claude 3 Opus

### Running the Hedge Fund

```bash
uv run src/main.py --ticker AAPL,MSFT,NVDA
```

**Example Output:**
<img width="992" alt="Screenshot 2025-01-06 at 5 50 17 PM" src="https://github.com/user-attachments/assets/e8ca04bf-9989-4a7d-a8b4-34e04666663b" />

You can also specify a `--show-reasoning` flag to print the reasoning of each agent to the console.

```bash
uv run src/main.py --ticker AAPL,MSFT,NVDA --show-reasoning
```

You can optionally specify the start and end dates to make decisions for a specific time period.

```bash
uv run src/main.py --ticker AAPL,MSFT,NVDA --start-date 2024-01-01 --end-date 2024-03-01
```

### Running the Backtester

```bash
uv run src/backtester.py --ticker AAPL,MSFT,NVDA
```

**Example Output:**
<img width="941" alt="Screenshot 2025-01-06 at 5 47 52 PM" src="https://github.com/user-attachments/assets/00e794ea-8628-44e6-9a84-8f8a31ad3b47" />

You can optionally specify the start and end dates to backtest over a specific time period.

```bash
uv run src/backtester.py --ticker AAPL,MSFT,NVDA --start-date 2024-01-01 --end-date 2024-03-01
```

## Project Structure
```
ai-hedge-fund/
├── src/
│   ├── agents/                   # Agent definitions and workflow
│   │   ├── bill_ackman.py        # Bill Ackman agent
│   │   ├── fundamentals.py       # Fundamental analysis agent
│   │   ├── portfolio_manager.py  # Portfolio management agent
│   │   ├── risk_manager.py       # Risk management agent
│   │   ├── sentiment.py          # Sentiment analysis agent
│   │   ├── technicals.py         # Technical analysis agent
│   │   ├── valuation.py          # Valuation analysis agent
│   │   ├── warren_buffett.py     # Warren Buffett agent
│   ├── tools/                    # Agent tools
│   │   ├── api.py                # API tools
│   ├── backtester.py             # Backtesting tools
│   ├── main.py                   # Main entry point
├── pyproject.toml                # Project configuration
├── uv.lock                       # Dependency lockfile (auto-generated)
├── ...
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

**Important**: Please keep your pull requests small and focused. This will make it easier to review and merge.

## Feature Requests

If you have a feature request, please open an [issue](https://github.com/virattt/ai-hedge-fund/issues) and make sure it is tagged with `enhancement`.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
