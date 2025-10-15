# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from .tool_params import baseToolArgs
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class GenericOpenSearchApiArgs(baseToolArgs):
    """Arguments for the generic OpenSearch API tool."""
    
    path: str = Field(
        description='The API endpoint path (e.g., "/_search", "/_cat/indices", "/my_index/_doc/1"). Should start with "/".'
    )
    method: str = Field(
        default='GET',
        description='HTTP method to use (GET, POST, PUT, DELETE, HEAD, PATCH)'
    )
    query_params: Optional[Dict[str, Any]] = Field(
        default=None,
        description='Query parameters to include in the request URL as key-value pairs'
    )
    body: Optional[Any] = Field(
        default=None,
        description='Request body for GET/POST/PUT requests. Can be a JSON object, string, or None'
    )
    headers: Optional[Dict[str, str]] = Field(
        default=None,
        description='Additional HTTP headers to include in the request'
    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "path": "/_search",
                    "method": "GET",
                    "query_params": {"size": 10, "from": 0}
                },
                {
                    "path": "/_cat/indices",
                    "method": "GET",
                    "query_params": {"format": "json", "v": True}
                },
                {
                    "path": "/my_index/_doc",
                    "method": "POST",
                    "body": {"title": "Test Document", "content": "This is a test"}
                },
                {
                    "path": "/my_index/_search",
                    "method": "POST",
                    "body": {
                        "query": {
                            "match": {"title": "search term"}
                        }
                    }
                },
                {
                    "path": "/_cluster/health",
                    "method": "GET"
                }
            ]
        }


async def generic_opensearch_api_tool(args: GenericOpenSearchApiArgs) -> list[dict]:
    """Generic OpenSearch API tool that can call any OpenSearch endpoint.
    
    This tool provides a flexible interface to interact with any OpenSearch API endpoint.
    It leverages the LLM's knowledge of OpenSearch APIs to construct appropriate requests.
    
    Use this tool when you need to:
    - Call OpenSearch APIs that don't have dedicated tools
    - Perform complex API operations with custom parameters
    - Access newer OpenSearch features not yet covered by specific tools
    - Combine multiple API calls in a workflow
    
    The tool supports all HTTP methods and can handle query parameters, request bodies,
    and custom headers. It uses the same authentication and connection logic as other tools.
    
    Write operations (POST, PUT, DELETE, PATCH) are only allowed when write 
    operations are enabled via configuration.
    
    Args:
        args: GenericOpenSearchApiArgs containing the API request details
        
    Returns:
        list[dict]: API response in MCP format
    """
    try:
        # Validate method
        valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'PATCH']
        method = args.method.upper()
        if method not in valid_methods:
            return [{'type': 'text', 'text': f'Error: Invalid HTTP method "{args.method}". Valid methods are: {", ".join(valid_methods)}'}]
        
        # Check if write operations are allowed using the global setting
        allow_write = get_allow_write_setting()
        write_methods = ['POST', 'PUT', 'DELETE', 'PATCH']
        
        if method in write_methods and not allow_write:
            return [{'type': 'text', 'text': f'Error: Write operations are disabled. Method "{method}" is not allowed. Enable write operations by setting OPENSEARCH_SETTINGS_ALLOW_WRITE=true or configuring allow_write: true in your config file.'}]
        
        # Validate path
        if not args.path.startswith('/'):
            return [{'type': 'text', 'text': 'Error: API path must start with "/"'}]
        
        # Initialize OpenSearch client
        client = initialize_client(args)
        
        # Build the request URL
        url = args.path
        if args.query_params:
            # Convert query parameters to URL-encoded string
            query_string = urlencode(args.query_params)
            url = f"{args.path}?{query_string}"
        
        # Prepare request parameters
        request_params = {
            'method': method,
            'url': url
        }
        
        # Add body for methods that support it
        if args.body is not None and method in ['POST', 'PUT', 'PATCH']:
            if isinstance(args.body, (dict, list)):
                request_params['body'] = json.dumps(args.body)
            else:
                request_params['body'] = args.body
        
        # Add custom headers if provided
        if args.headers:
            request_params['headers'] = args.headers
        
        # Make the API request using the transport layer
        logger.info(f"Making {method} request to {url}")
        response = client.transport.perform_request(**request_params)
        
        # Format the response
        if isinstance(response, str):
            # Some APIs return plain text (like hot_threads)
            formatted_response = response
        else:
            # Most APIs return JSON
            formatted_response = json.dumps(response, indent=2)
        
        # Create descriptive message
        message = f"OpenSearch API Response ({method} {args.path})"
        if args.query_params:
            message += f" with query params: {args.query_params}"
        
        return [{'type': 'text', 'text': f'{message}:\n{formatted_response}'}]
        
    except Exception as e:
        error_message = f'Error calling OpenSearch API ({args.method} {args.path}): {str(e)}'
        logger.error(error_message)
        return [{'type': 'text', 'text': error_message}]