
import os
import json
import re
from datetime import datetime
from google.cloud import bigquery
from google.oauth2 import service_account
from fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP(
    "sf-311-bigquery",
    instructions="An MCP Server to query and analyze San Francisco 311 municipal service requests using Google BigQuery public datasets."
)

TABLE_ID = "bigquery-public-data.san_francisco.311_service_requests"

def get_bigquery_client() -> bigquery.Client:
    """
    Initializes and returns a BigQuery client using available credentials.
    Supports:
    1. BIGQUERY_CREDENTIALS_JSON - Env var containing raw service account JSON string
    2. GOOGLE_APPLICATION_CREDENTIALS - Env var pointing to service account file path
    3. Standard Application Default Credentials (ADC) or Metadata Server
    """
    creds_json = os.environ.get("BIGQUERY_CREDENTIALS_JSON")
    if creds_json:
        try:
            creds_info = json.loads(creds_json)
            credentials = service_account.Credentials.from_service_account_info(creds_info)
            project_id = creds_info.get("project_id") or os.environ.get("GOOGLE_CLOUD_PROJECT")
            return bigquery.Client(credentials=credentials, project=project_id)
        except Exception as e:
            # Fallback but print error
            print(f"Warning: Failed to load credentials from BIGQUERY_CREDENTIALS_JSON: {e}")
            
    # Traditional ADC path (handles GOOGLE_APPLICATION_CREDENTIALS automatically)
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    return bigquery.Client(project=project_id)


def serialize_row(row):
    """Converts a BigQuery Row object to a dictionary, handling datetimes/timestamps."""
    data = dict(row)
    for key, val in data.items():
        if isinstance(val, (datetime, datetime.date)):
            data[key] = val.isoformat()
    return data


@mcp.tool()
def get_request_status(case_id: str) -> str:
    """
    Retrieve full details of a specific 311 service request by its unique_key (case_id).

    Args:
        case_id: The unique identifier (unique_key) of the 311 request (e.g. "12345678").
    """
    try:
        client = get_bigquery_client()
        query = f"""
        SELECT *
        FROM `{TABLE_ID}`
        WHERE unique_key = @case_id
        LIMIT 1
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("case_id", "STRING", case_id)
            ]
        )
        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        if not results:
            return f"No 311 service request found with unique_key/case_id: {case_id}"
            
        row_dict = serialize_row(results[0])
        return json.dumps(row_dict, indent=2)
    except Exception as e:
        return f"Error retrieving request status: {str(e)}"


@mcp.tool()
def search_requests(
    status: str = None,
    category: str = None,
    neighborhood: str = None,
    supervisor_district: int = None,
    limit: int = 50,
    days_back: int = 30
) -> str:
    """
    Search for recent SF 311 service requests with various filters.

    Args:
        status: Filter by status, e.g., 'Open' or 'Closed'.
        category: Filter by category (e.g., 'Pothole', 'Graffiti', 'Streetlight'). Case-insensitive partial match.
        neighborhood: Filter by neighborhood name (e.g., 'Mission', 'SOMA', 'Tenderloin'). Case-insensitive.
        supervisor_district: Filter by SF supervisor district number (1 through 11).
        limit: Maximum number of results to return (max 100, default 50).
        days_back: Number of days back to search from today (default 30, use 0 or larger values to search further back).
    """
    try:
        client = get_bigquery_client()
        where_clauses = []
        query_params = []
        
        if days_back and days_back > 0:
            where_clauses.append("created_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days_back DAY)")
            query_params.append(bigquery.ScalarQueryParameter("days_back", "INT64", days_back))
            
        if status:
            where_clauses.append("status = @status")
            query_params.append(bigquery.ScalarQueryParameter("status", "STRING", status))
            
        if category:
            where_clauses.append("LOWER(category) LIKE @category")
            query_params.append(bigquery.ScalarQueryParameter("category", "STRING", f"%{category.lower()}%"))
            
        if neighborhood:
            where_clauses.append("LOWER(neighborhood) = @neighborhood")
            query_params.append(bigquery.ScalarQueryParameter("neighborhood", "STRING", neighborhood.lower()))
            
        if supervisor_district is not None:
            where_clauses.append("supervisor_district = @supervisor_district")
            query_params.append(bigquery.ScalarQueryParameter("supervisor_district", "INT64", supervisor_district))
            
        # Enforce maximum limit of 100 for safety
        limit = min(max(1, limit), 100)
        query_params.append(bigquery.ScalarQueryParameter("limit", "INT64", limit))
        
        where_str = ""
        if where_clauses:
            where_str = "WHERE " + " AND ".join(where_clauses)
            
        query = f"""
        SELECT unique_key, created_date, closed_date, status, agency_name, category, complaint_type, descriptor, neighborhood, supervisor_district, latitude, longitude
        FROM `{TABLE_ID}`
        {where_str}
        ORDER BY created_date DESC
        LIMIT @limit
        """
        
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        query_job = client.query(query, job_config=job_config)
        results = [serialize_row(row) for row in query_job.result()]
        
        if not results:
            return "No service requests matched the search criteria."
            
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error executing search: {str(e)}"


@mcp.tool()
def get_top_complaints(
    neighborhood: str = None,
    days_back: int = 30,
    limit: int = 10
) -> str:
    """
    Get the top complaint categories or types overall or in a specific neighborhood.

    Args:
        neighborhood: Optional neighborhood to filter by (e.g. 'Mission').
        days_back: Number of days back to look (default 30).
        limit: Number of top complaints to return (default 10).
    """
    try:
        client = get_bigquery_client()
        where_clauses = []
        query_params = []
        
        if days_back and days_back > 0:
            where_clauses.append("created_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days_back DAY)")
            query_params.append(bigquery.ScalarQueryParameter("days_back", "INT64", days_back))
            
        if neighborhood:
            where_clauses.append("LOWER(neighborhood) = @neighborhood")
            query_params.append(bigquery.ScalarQueryParameter("neighborhood", "STRING", neighborhood.lower()))
            
        limit = min(max(1, limit), 50)
        query_params.append(bigquery.ScalarQueryParameter("limit", "INT64", limit))
        
        where_str = ""
        if where_clauses:
            where_str = "WHERE " + " AND ".join(where_clauses)
            
        query = f"""
        SELECT category, COUNT(*) as count
        FROM `{TABLE_ID}`
        {where_str}
        GROUP BY category
        ORDER BY count DESC
        LIMIT @limit
        """
        
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        query_job = client.query(query, job_config=job_config)
        results = [serialize_row(row) for row in query_job.result()]
        
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error getting top complaints: {str(e)}"


@mcp.tool()
def get_neighborhood_summary(days_back: int = 30, limit: int = 20) -> str:
    """
    Get a summary of 311 activity across different neighborhoods (total, open, closed requests).

    Args:
        days_back: Number of days back to analyze (default 30).
        limit: Number of neighborhoods to return, sorted by most active (default 20).
    """
    try:
        client = get_bigquery_client()
        query_params = []
        
        where_clause = ""
        if days_back and days_back > 0:
            where_clause = "WHERE created_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days_back DAY) AND neighborhood IS NOT NULL"
            query_params.append(bigquery.ScalarQueryParameter("days_back", "INT64", days_back))
        else:
            where_clause = "WHERE neighborhood IS NOT NULL"
            
        limit = min(max(1, limit), 50)
        query_params.append(bigquery.ScalarQueryParameter("limit", "INT64", limit))
        
        query = f"""
        SELECT neighborhood, 
               COUNT(*) as total_requests,
               COUNTIF(status = 'Open') as open_requests,
               COUNTIF(status = 'Closed') as closed_requests
        FROM `{TABLE_ID}`
        {where_clause}
        GROUP BY neighborhood
        ORDER BY total_requests DESC
        LIMIT @limit
        """
        
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        query_job = client.query(query, job_config=job_config)
        results = [serialize_row(row) for row in query_job.result()]
        
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error getting neighborhood summary: {str(e)}"


@mcp.tool()
def get_resolution_metrics(category: str = None, days_back: int = 90) -> str:
    """
    Get average resolution times (in hours and days) for closed 311 requests.

    Args:
        category: Optional category to filter or search for (e.g. 'Pothole'). Case-insensitive.
        days_back: Number of days back to look for closed requests (default 90).
    """
    try:
        client = get_bigquery_client()
        where_clauses = ["status = 'Closed'", "closed_date >= created_date"]
        query_params = []
        
        if days_back and days_back > 0:
            where_clauses.append("created_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days_back DAY)")
            query_params.append(bigquery.ScalarQueryParameter("days_back", "INT64", days_back))
            
        if category:
            where_clauses.append("LOWER(category) LIKE @category")
            query_params.append(bigquery.ScalarQueryParameter("category", "STRING", f"%{category.lower()}%"))
            
        where_str = "WHERE " + " AND ".join(where_clauses)
        
        query = f"""
        SELECT category, 
               COUNT(*) as closed_count,
               ROUND(AVG(TIMESTAMP_DIFF(closed_date, created_date, HOUR)), 1) as avg_resolution_hours,
               ROUND(AVG(TIMESTAMP_DIFF(closed_date, created_date, DAY)), 1) as avg_resolution_days
        FROM `{TABLE_ID}`
        {where_str}
        GROUP BY category
        ORDER BY avg_resolution_hours DESC
        LIMIT 50
        """
        
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        query_job = client.query(query, job_config=job_config)
        results = [serialize_row(row) for row in query_job.result()]
        
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error getting resolution metrics: {str(e)}"


@mcp.tool()
def run_custom_query(sql_query: str) -> str:
    """
    Execute a safe, custom read-only SELECT query against the SF 311 dataset.
    Use this for advanced analytics, trends, or complex aggregations.

    Requirements and Guardrails:
    - Must be a SELECT query.
    - Must reference the '311_service_requests' table.
    - Cannot contain modifying keywords (e.g. INSERT, UPDATE, DELETE, DROP, CREATE, ALTER).
    - Result count is strictly limited to 100 rows.

    Example Query:
    SELECT FORMAT_DATETIME('%A', created_date) as day_of_week, count(*) as count 
    FROM `bigquery-public-data.san_francisco.311_service_requests` 
    WHERE created_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY) 
    GROUP BY day_of_week 
    ORDER BY count DESC
    """
    try:
        query_upper = sql_query.upper()
        
        # Enforce SELECT
        if "SELECT" not in query_upper:
            return "Error: Only read-only SELECT queries are allowed."
            
        # Enforce reference to our table
        if "311_SERVICE_REQUESTS" not in query_upper:
            return f"Error: Queries must be run against the '{TABLE_ID}' table."
            
        # Reject modifying queries
        for forbidden in ["INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "GRANT", "REVOKE", "MERGE"]:
            if re.search(r'\b' + forbidden + r'\b', query_upper):
                return f"Error: Query contains forbidden SQL keyword: {forbidden}"
                
        # Enforce limit of 100 rows
        # If there's already a limit, we'll parse it and cap it at 100, or we'll append a limit.
        limit_match = re.search(r'\bLIMIT\s+(\d+)\b', query_upper)
        if limit_match:
            val = int(limit_match.group(1))
            if val > 100:
                # Replace the limit with 100
                sql_query = re.sub(r'\bLIMIT\s+\d+\b', "LIMIT 100", sql_query, flags=re.IGNORECASE)
        else:
            sql_query = f"{sql_query} LIMIT 100"
            
        client = get_bigquery_client()
        query_job = client.query(sql_query)
        results = [serialize_row(row) for row in query_job.result()]
        
        if not results:
            return "Query completed successfully, but returned no results."
            
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error executing custom query: {str(e)}"


if __name__ == "__main__":
    # When deployed to Cloud Run or running as a web service, PORT is specified.
    # We default to SSE transport if PORT is defined.
    if "PORT" in os.environ:
        from starlette.middleware import Middleware
        from starlette.middleware.cors import CORSMiddleware

        port = int(os.environ.get("PORT", 8080))
        mcp.run(
            transport="sse",
            host="0.0.0.0",
            port=port,
            middleware=[
                Middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_methods=["*"],
                    allow_headers=["*"],
                )
            ],
        )
    else:
        mcp.run()
