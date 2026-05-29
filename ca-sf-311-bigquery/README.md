# San Francisco 311 BigQuery MCP Server

An MCP (Model Context Protocol) Server written in Python using `FastMCP` that connects to Google Cloud BigQuery's public datasets to search, analyze, and query **San Francisco 311 municipal service requests**.

This server enables LLM agents to investigate municipal complaints, analyze trends, track resolution speeds, explore neighborhoods, and run raw, safe read-only SQL queries against live public datasets containing millions of records.

---

## 🛠 Features & Exposed Tools

The server registers 6 high-level tools to give AI agents deep access to SF 311 records:

1. **`get_request_status(case_id: str)`**
   * Retrieve full details of a specific 311 service request by its unique case identifier.

2. **`search_requests(...)`**
   * Search for recent 311 requests with powerful filters including status (`Open`/`Closed`), category (e.g. `Pothole`, `Graffiti`), neighborhood (e.g. `Mission`), supervisor district, and a configurable history window (`days_back`).

3. **`get_top_complaints(...)`**
   * Aggregate and retrieve the top-ranking complaint categories overall or filtered by neighborhood over a specified date range.

4. **`get_neighborhood_summary(...)`**
   * Summarize 311 request activity by neighborhood (total requests, open count, closed count) to quickly find active civic areas.

5. **`get_resolution_metrics(...)`**
   * Calculate average resolution speeds (in both hours and days) grouped by complaint category.

6. **`run_custom_query(sql_query: str)`**
   * Runs custom read-only `SELECT` queries against the BigQuery `311_service_requests` table with safety guardrails (auto-enforced limit of 100 records and rejection of modifying statements like `UPDATE`/`DELETE`).

---

## 🚀 Setup & Installation

### 1. Prerequisites

Make sure you have Python 3.10+ installed.

### 2. Install Dependencies

In your terminal, navigate to this directory and install the required packages:

```bash
pip install -r requirements.txt
```

---

## 🔐 Google Cloud Authentication

BigQuery requires Google Cloud credentials for API calls, even when querying public datasets (to track query billing). You can authenticate in one of three ways:

### Option A: Use Application Default Credentials (ADC) - Recommended for Local Dev

If you have the Google Cloud CLI (`gcloud`) installed, simply run this command in your terminal and log in with your Google Account:

```bash
gcloud auth application-default login
```

The Python BigQuery library will automatically locate and use these credentials. You can also specify your default project:

```bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
```

### Option B: Raw Service Account JSON String (Great for Codespaces/Containers)

If you are developing in GitHub Codespaces or a Docker container, it is often easiest to pass a Service Account's key file as a raw JSON string using the `BIGQUERY_CREDENTIALS_JSON` environment variable:

```bash
export BIGQUERY_CREDENTIALS_JSON='{
  "type": "service_account",
  "project_id": "your-gcp-project",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "...",
  ...
}'
```

### Option C: Service Account JSON File Path

Download a Service Account key file from the Google Cloud Console and set the environment variable pointing to its path:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account.json"
```

---

## 🔌 Running and Testing

### 1. Interactive Testing via MCP Inspector

You can quickly launch the server and explore its tools interactively using the official `@modelcontextprotocol/inspector`:

```bash
npx -y @modelcontextprotocol/inspector python3 /workspaces/coffee-code/ca-sf-311-bigquery/server.py
```

This will spin up a local web UI where you can test each tool, supply parameters, and see the exact JSON responses returned from Google BigQuery.

### 2. Running Standalone

To run the server directly via stdio transport:

```bash
python3 server.py
```

---

## 🤖 Configuring in AI Client Applications

To integrate this server into an AI-powered editor or developer tool, register it in your client's MCP configuration file (typically `mcp_config.json` or `config.json`):

```json
{
  "mcpServers": {
    "sf-311-bigquery": {
      "command": "python3",
      "args": [
        "/workspaces/coffee-code/ca-sf-311-bigquery/server.py"
      ],
      "env": {
        "GOOGLE_CLOUD_PROJECT": "your-gcp-project-id",
        "BIGQUERY_CREDENTIALS_JSON": "optional-raw-service-account-json-string-here"
      }
    }
  }
}
```

---

## 📊 Sample Prompts for AI Agents

Once connected, you can ask your agent questions like:

*   *"Show me the 5 most recent service requests in the Mission neighborhood."*
*   *"What are the top 10 municipal issues in San Francisco over the last 30 days?"*
*   *"Which SF neighborhood has the highest number of open 311 requests?"*
*   *"How long on average does it take the city to resolve Pothole vs. Graffiti issues?"*
*   *"Can you run a query to count the number of complaints opened per day of the week over the last month?"*
