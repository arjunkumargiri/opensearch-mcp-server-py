![OpenSearch logo](https://github.com/opensearch-project/opensearch-py/raw/main/OpenSearch.svg)

# OpenSearch-mcp-server-py User Guide

## Quick Start

### Prerequisite: 
Install `uv` via `pip` or [standalone installer](https://github.com/astral-sh/uv?tab=readme-ov-file#installation):
```
pip install uv
```

The OpenSearch MCP server can be used via `uvx`, no installation required. Therefore, we just need to configure our AI agent of choice.

For [Q Developer CLI](https://github.com/aws/amazon-q-developer-cli), configure `~/.aws/amazonq/mcp.json` with the configuration below. See [here](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-mcp-configuration.html) for additional configuration options.

For Claude Desktop, configure `claude_desktop_config.json` from Settings > Developer. See [here](https://modelcontextprotocol.io/quickstart/user#2-add-the-filesystem-mcp-server) for more details on using MCP with Claude Desktop.
```
{
  "mcpServers": {
    "opensearch-mcp-server": {
      "command": "uvx",
      "args": [
        "opensearch-mcp-server-py"
      ],
      "env": {
        // Optional
        "OPENSEARCH_URL": "<your_opensearch_domain_url>",
        
        // For OpenSearch Serverless
        "AWS_OPENSEARCH_SERVERLESS": "true",  // Set to "true" for OpenSearch Serverless

        // For Basic Authentication
        "OPENSEARCH_USERNAME": "<your_opensearch_domain_username>",
        "OPENSEARCH_PASSWORD": "<your_opensearch_domain_password>",

        // For IAM Role Authentication
        "AWS_REGION": "<your_aws_region>",
        "AWS_ACCESS_KEY_ID": "<your_aws_access_key>",
        "AWS_SECRET_ACCESS_KEY": "<your_aws_secret_access_key>",
        "AWS_SESSION_TOKEN": "<your_aws_session_token>"
      }
    }
  }
}
```

That's it! You are now ready to use your AI agent with OpenSearch tools.
Please note that if the `OPENSEARCH_URL` is not set via the environment variables, it must be provided as an argument during tool invocation.

## Installation

Use the below steps if you would like to install `opensearch-mcp-server-py` locally.

Install from [PyPI](https://pypi.org/project/opensearch-mcp-server-py/):
```
pip install opensearch-mcp-server-py
```

### Sample configuration
```
{
    "mcpServers": {
        "opensearch-mcp-server": {
            "command": "python",  // Or full path to python with PyPI package installed
            "args": [
                "-m",
                "mcp_server_opensearch"
            ],
            "env": {
                // Optional
                "OPENSEARCH_URL": "<your_opensearch_domain_url>",
                
                // For OpenSearch Serverless
                "AWS_OPENSEARCH_SERVERLESS": "true",  // Set to "true" for OpenSearch Serverless

                // For Basic Authentication
                "OPENSEARCH_USERNAME": "<your_opensearch_domain_username>",
                "OPENSEARCH_PASSWORD": "<your_opensearch_domain_password>",

                // For IAM Role Authentication
                "AWS_REGION": "<your_aws_region>",
                "AWS_ACCESS_KEY_ID": "<your_aws_access_key>",
                "AWS_SECRET_ACCESS_KEY": "<your_aws_secret_access_key>",
                "AWS_SESSION_TOKEN": "<your_aws_session_token>"
            }
        }
    }
}
```

## Configuration

Both basic authentication and IAM authentication can be configured via either global environment variables or environment variables in agent MCP config file.

### Authentication Methods:
- **Basic Authentication**
```
export OPENSEARCH_URL="<your_opensearch_domain_url>"
export OPENSEARCH_USERNAME="<your_opensearch_domain_username>"
export OPENSEARCH_PASSWORD="<your_opensearch_domain_password>"
```

- **IAM Role Authentication**
```
export OPENSEARCH_URL="<your_opensearch_domain_url>"
export AWS_REGION="<your_aws_region>"
export AWS_ACCESS_KEY_ID="<your_aws_access_key>"
export AWS_SECRET_ACCESS_KEY="<your_aws_secret_access_key>"
export AWS_SESSION_TOKEN="<your_aws_session_token>"
```

- **OpenSearch Serverless**
```
export OPENSEARCH_URL="<your_opensearch_serverless_endpoint>"
export AWS_OPENSEARCH_SERVERLESS=true
export AWS_REGION="<your_aws_region>"
export AWS_ACCESS_KEY_ID="<your_aws_access_key>"
export AWS_SECRET_ACCESS_KEY="<your_aws_secret_access_key>"
export AWS_SESSION_TOKEN="<your_aws_session_token>"
```

### Running the Server:
```
# Stdio Server
python -m mcp_server_opensearch

# SSE Server
python -m mcp_server_opensearch --transport sse
```

## LangChain Integration
The OpenSearch MCP server can be easily integrated with LangChain using the SSE server transport

### Prerequisites
1. Install required packages
```
pip install langchain langchain-mcp-adapters langchain-openai
```
2. Set up OpenAI API key
```
export OPENAI_API_KEY="<your-openai-key>"
```
3. Ensure OpenSearch MCP server is running in SSE mode
```
python -m mcp_server_opensearch --transport sse
```

### Example Integration Script
``` python 
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain.agents import AgentType, initialize_agent

# Initialize LLM (can use any LangChain-compatible LLM)
model = ChatOpenAI(model="gpt-4o")

async def main():
    # Connect to MCP server and create agent
    async with MultiServerMCPClient({
        "opensearch-mcp-server": {
            "transport": "sse",
            "url": "http://localhost:9900/sse",  # SSE server endpoint
            "headers": {
                "Authorization": "Bearer secret-token",
            }
        }
    }) as client:
        tools = client.get_tools()
        agent = initialize_agent(
            tools=tools,
            llm=model,
            agent=AgentType.OPENAI_FUNCTIONS,
            verbose=True,  # Enables detailed output of the agent's thought process
        )

        # Example query
        await agent.ainvoke({"input": "List all indices"})

if __name__ == "__main__":
    asyncio.run(main())
```
**Notes:**
- The script is compatible with any LLM that integrates with LangChain and supports tool calling
- Make sure the OpenSearch MCP server is running before executing the script
- Configure authentication and environment variables as needed
