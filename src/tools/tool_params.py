# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

from pydantic import BaseModel, Field
from typing import Any, Optional, Type, TypeVar, Dict
from mcp_server_opensearch.global_state import get_mode

T = TypeVar('T', bound=BaseModel)


def validate_args_for_mode(args_dict: Dict[str, Any], args_model_class: Type[T]) -> T:
    """
    Validation middleware that handles mode-specific validation.

    Args:
        args_dict: Dictionary of arguments provided by the user
        args_model_class: The Pydantic model class to validate against

    Returns:
        Validated instance of args_model_class
    """
    # Get the current mode from global state
    mode = get_mode()

    if mode == 'single':
        # In single mode, add default values for base fields
        args_dict = args_dict.copy()  # Don't modify the original
        args_dict.setdefault('opensearch_cluster_name', '')

    try:
        return args_model_class(**args_dict)
    except Exception as e:
        # Create a consistent error message format for both modes
        import re

        error_str = str(e)

        # Extract missing field names and create a clearer error message
        missing_fields = re.findall(r'^(\w+)\n  Field required', error_str, re.MULTILINE)
        if missing_fields:
            field_list = ', '.join(f"'{field}'" for field in missing_fields)
            if len(missing_fields) == 1:
                error_msg = f'Missing required field: {field_list}'
            else:
                error_msg = f'Missing required fields: {field_list}'

            # For single mode, show user input without opensearch_cluster_name
            if mode == 'single':
                user_input = {k: v for k, v in args_dict.items() if k != 'opensearch_cluster_name'}
                error_msg += f'\n\nProvided: {user_input}'
            else:
                error_msg += f'\n\nProvided: {args_dict}'

            raise ValueError(error_msg) from e

        raise e


class baseToolArgs(BaseModel):
    """Base class for all tool arguments that contains common OpenSearch connection parameters."""

    opensearch_cluster_name: str = Field(description='The name of the OpenSearch cluster')


class ListIndicesArgs(baseToolArgs):
    index: str = Field(
        default='',
        description='The name of the index or index pattern to get information for.',
    )
    include_detail: bool = Field(
        default=True,
        description='Whether to include detailed information. If False, returns only index name(s). If True, returns full metadata.',
    )


class GetIndexMappingArgs(baseToolArgs):
    index: str = Field(description='The name of the index to get mapping information for')


class SearchIndexArgs(baseToolArgs):
    index: str = Field(description='The name of the index to search in')
    query: Any = Field(description='The search query in OpenSearch query DSL format')
    format: str = Field(default='json', description='Output format: "json" or "csv"')
    size: int = Field(default=10, description='Number of search results to return. The maximum allowed value is 100, unless overridden by configuration.')


class GetShardsArgs(baseToolArgs):
    index: str = Field(description='The name of the index to get shard information for')


class GetClusterStateArgs(baseToolArgs):
    """Arguments for the GetClusterStateTool."""

    metric: Optional[str] = Field(
        default=None,
        description='Limit the information returned to the specified metrics. Options include: _all, blocks, metadata, nodes, routing_table, routing_nodes, master_node, version',
    )
    index: Optional[str] = Field(
        default=None, description='Limit the information returned to the specified indices'
    )

    class Config:
        json_schema_extra = {
            'examples': [{'metric': 'nodes', 'index': 'my_index'}, {'metric': '_all'}]
        }


class GetSegmentsArgs(baseToolArgs):
    """Arguments for the GetSegmentsTool."""

    index: Optional[str] = Field(
        default=None,
        description='Limit the information returned to the specified indices. If not provided, returns segments for all indices.',
    )

    class Config:
        json_schema_extra = {
            'examples': [
                {'index': 'my_index'},
                {},  # Empty example to show all segments
            ]
        }


class CatNodesArgs(baseToolArgs):
    """Arguments for the CatNodesTool."""

    metrics: Optional[str] = Field(
        default=None,
        description='A comma-separated list of metrics to display. Available metrics include: id, name, ip, port, role, master, heap.percent, ram.percent, cpu, load_1m, load_5m, load_15m, disk.total, disk.used, disk.avail, disk.used_percent',
    )

    class Config:
        json_schema_extra = {
            'examples': [
                {'metrics': 'name,ip,heap.percent,cpu,load_1m'},
                {},  # Empty example to show all node metrics
            ]
        }


class GetIndexInfoArgs(baseToolArgs):
    """Arguments for the GetIndexInfoTool."""

    index: str = Field(
        description='The name of the index to get detailed information for. Wildcards are supported.'
    )

    class Config:
        json_schema_extra = {
            'examples': [
                {'index': 'my_index'},
                {
                    'index': 'my_index*'  # Using wildcard
                },
            ]
        }


class GetIndexStatsArgs(baseToolArgs):
    """Arguments for the GetIndexStatsTool."""

    index: str = Field(
        description='The name of the index to get statistics for. Wildcards are supported.'
    )
    metric: Optional[str] = Field(
        default=None,
        description='Limit the information returned to the specified metrics. Options include: _all, completion, docs, fielddata, flush, get, indexing, merge, query_cache, refresh, request_cache, search, segments, store, warmer, bulk',
    )

    class Config:
        json_schema_extra = {
            'examples': [{'index': 'my_index'}, {'index': 'my_index', 'metric': 'search,indexing'}]
        }


class GetQueryInsightsArgs(baseToolArgs):
    """Arguments for the GetQueryInsightsTool."""

    # No additional parameters needed for the basic implementation
    # The tool will simply call GET /_insights/top_queries without parameters

    class Config:
        json_schema_extra = {
            'examples': [
                {}  # Empty example as no additional parameters are required
            ]
        }


class GetNodesHotThreadsArgs(baseToolArgs):
    """Arguments for the GetNodesHotThreadsTool."""

    # No additional parameters needed for the basic implementation
    # The tool will simply call GET /_nodes/hot_threads without parameters

    class Config:
        json_schema_extra = {
            'examples': [
                {}  # Empty example as no additional parameters are required
            ]
        }


class GetAllocationArgs(baseToolArgs):
    """Arguments for the GetAllocationTool."""

    # No additional parameters needed for the basic implementation
    # The tool will simply call GET /_cat/allocation without parameters

    class Config:
        json_schema_extra = {
            'examples': [
                {}  # Empty example as no additional parameters are required
            ]
        }


class GetLongRunningTasksArgs(baseToolArgs):
    """Arguments for the GetLongRunningTasksTool."""

    limit: Optional[int] = Field(
        default=10, description='The maximum number of tasks to return. Default is 10.'
    )

    class Config:
        json_schema_extra = {
            'examples': [
                {},  # Default example to show top 10 long-running tasks
                {
                    'limit': 5  # Example to show top 5 long-running tasks
                },
            ]
        }


class GetNodesArgs(baseToolArgs):
    """Arguments for the GetNodesTool."""

    node_id: Optional[str] = Field(
        default=None,
        description='A comma-separated list of node IDs or names to limit the returned information. Supports node filters like _local, _master, master:true, data:false, etc. Defaults to _all.',
    )
    metric: Optional[str] = Field(
        default=None,
        description='A comma-separated list of metric groups to include in the response. Options include: settings, os, process, jvm, thread_pool, transport, http, plugins, ingest, aggregations, indices. Defaults to all metrics.',
    )

    class Config:
        json_schema_extra = {
            'examples': [
                {},  # Get all nodes with all metrics
                {'node_id': 'master:true', 'metric': 'process,transport'},
                {'node_id': '_local', 'metric': 'jvm,os'},
            ]
        }
