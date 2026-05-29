import asyncio
import sys
from server import mcp

async def test_mcp():
    print("--- SF 311 BigQuery MCP Server Tool Verification ---")
    print("Listing registered tools:")
    try:
        # Await the asynchronous list_tools() call
        tools = await mcp.list_tools()
        for tool in tools:
            print(f" - {tool.name}: {tool.description.strip().splitlines()[0] if tool.description else 'No description'}")
    except Exception as e:
        print(f"Error listing tools: {e}")
    
    print("\nAttempting to call 'get_top_complaints' tool locally...")
    try:
        # Await the asynchronous call_tool() call
        result = await mcp.call_tool("get_top_complaints", {"limit": 3, "days_back": 30})
        print("\nSuccess! Result:")
        print(result)
    except Exception as e:
        print(f"\nCould not run local test query: {e}", file=sys.stderr)
        print("\nNote: Please make sure your Google Cloud credentials (ADC or BIGQUERY_CREDENTIALS_JSON) are configured.")

if __name__ == "__main__":
    asyncio.run(test_mcp())
