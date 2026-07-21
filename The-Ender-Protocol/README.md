# The Ender Protocol

An AI training platform disguised as a game. A human player, assisted by a "Jedi Co-Pilot" agent, plays against an autonomous "Sith Infiltrator" agent.

## Architecture

- **AWS Lambda**: Serverless compute for all agents
- **Amazon Bedrock**: AI agents (Jedi Co-Pilot & Sith Infiltrator)
- **Amazon S3**: Data storage for scenarios and game state
- **Python 3.11**: All Lambda functions use Boto3

## Project Structure

```
The-Ender-Protocol/
├── /scenarios
│   └── /scenario_01_bruteforce
│       ├── user_accounts.json
│       └── password_dictionary.json
├── /src
│   └── /lambdas
│       ├── /supervisor_agent
│       │   └── app.py
│       ├── /red_team_tools
│       │   └── app.py
│       └── /blue_team_tools
│           └── app.py
└── README.md
```

## Agents

- **Supervisor Agent**: Orchestrates the game, manages state, enforces rules
- **Jedi Co-Pilot**: Assists human player (Blue Team)
- **Sith Infiltrator**: Autonomous adversary (Red Team)

## Security

- IAM roles for all AWS service access
- No hardcoded credentials
- Principle of least privilege
