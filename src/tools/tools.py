# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import json
from .tool_params import (
    GetAllocationArgs,
    GetClusterStateArgs,
    GetIndexInfoArgs,
    GetIndexMappingArgs,
    GetIndexStatsArgs,
    GetLongRunningTasksArgs,
    CatNodesArgs,
    GetNodesArgs,
    GetNodesHotThreadsArgs,
    GetQueryInsightsArgs,
    GetSegmentsArgs,
    GetShardsArgs,
    ListIndicesArgs,
    SearchIndexArgs,
    baseToolArgs,
)
from .utils import is_tool_compatible
from opensearch.helper import (
    get_allocation,
    get_cluster_state,
    get_index,
    get_index_info,
    get_index_mapping,
    get_index_stats,
    get_long_running_tasks,
    get_nodes,
    get_nodes_info,
    get_nodes_hot_threads,
    get_opensearch_version,
    get_query_insights,
    get_segments,
    get_shards,
    list_indices,
    search_index,
)


def check_tool_compatibility(tool_name: str, args: baseToolArgs = None):
    opensearch_version = get_opensearch_version(args)
    if not is_tool_compatible(opensearch_version, TOOL_REGISTRY[tool_name]):
        tool_display_name = TOOL_REGISTRY[tool_name].get('display_name', tool_name)
        min_version = TOOL_REGISTRY[tool_name].get('min_version', '')
        max_version = TOOL_REGISTRY[tool_name].get('max_version', '')

        version_info = (
            f'{min_version} to {max_version}'
            if min_version and max_version
            else f'{min_version} or later'
            if min_version
            else f'up to {max_version}'
            if max_version
            else None
        )

        error_message = f"Tool '{tool_display_name}' is not supported for this OpenSearch version (current version: {opensearch_version})."
        if version_info:
            error_message += f' Supported version: {version_info}.'

        raise Exception(error_message)


async def list_indices_tool(args: ListIndicesArgs) -> list[dict]:
    try:
        check_tool_compatibility('ListIndexTool', args)

        # If index is provided, always return detailed information for that specific index
        if args.index:
            index_info = get_index(args)
            formatted_info = json.dumps(index_info, indent=2)
            return [
                {'type': 'text', 'text': f'Index information for {args.index}:\n{formatted_info}'}
            ]

        # Otherwise, list all indices
        indices = list_indices(args)

        # If include_detail is False, return only pure list of index names
        if not args.include_detail:
            index_names = [
                item.get('index')
                for item in indices
                if isinstance(item, dict) and 'index' in item
            ]
            formatted_names = json.dumps(index_names, indent=2)
            return [{'type': 'text', 'text': f'Indices:\n{formatted_names}'}]

        # include_detail is True: return full information
        formatted_indices = json.dumps(indices, indent=2)
        return [{'type': 'text', 'text': f'All indices information:\n{formatted_indices}'}]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error listing indices: {str(e)}'}]


async def get_index_mapping_tool(args: GetIndexMappingArgs) -> list[dict]:
    try:
        check_tool_compatibility('IndexMappingTool', args)
        mapping = get_index_mapping(args)
        formatted_mapping = json.dumps(mapping, indent=2)

        return [{'type': 'text', 'text': f'Mapping for {args.index}:\n{formatted_mapping}'}]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error getting mapping: {str(e)}'}]


async def search_index_tool(args: SearchIndexArgs) -> list[dict]:
    try:
        check_tool_compatibility('SearchIndexTool', args)
        result = search_index(args)
        formatted_result = json.dumps(result, indent=2)

        return [
            {
                'type': 'text',
                'text': f'Search results from {args.index}:\n{formatted_result}',
            }
        ]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error searching index: {str(e)}'}]


async def get_shards_tool(args: GetShardsArgs) -> list[dict]:
    try:
        check_tool_compatibility('GetShardsTool', args)
        result = get_shards(args)

        if isinstance(result, dict) and 'error' in result:
            return [{'type': 'text', 'text': f'Error getting shards: {result["error"]}'}]
        formatted_text = 'index | shard | prirep | state | docs | store | ip | node\n'

        # Format each shard row
        for shard in result:
            formatted_text += f'{shard["index"]} | '
            formatted_text += f'{shard["shard"]} | '
            formatted_text += f'{shard["prirep"]} | '
            formatted_text += f'{shard["state"]} | '
            formatted_text += f'{shard["docs"]} | '
            formatted_text += f'{shard["store"]} | '
            formatted_text += f'{shard["ip"]} | '
            formatted_text += f'{shard["node"]}\n'

        return [{'type': 'text', 'text': formatted_text}]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error getting shards information: {str(e)}'}]


async def get_cluster_state_tool(args: GetClusterStateArgs) -> list[dict]:
    """Tool to get the current state of the cluster.
    
    Args:
        args: GetClusterStateArgs containing optional metric and index filters
        
    Returns:
        list[dict]: Cluster state information in MCP format
    """
    try:
        check_tool_compatibility('GetClusterStateTool', args)
        result = get_cluster_state(args)
        
        # Format the response for better readability
        formatted_result = json.dumps(result, indent=2)
        
        # Create response message based on what was requested
        message = "Cluster state information"
        if args.metric:
            message += f" for metric: {args.metric}"
        if args.index:
            message += f", filtered by index: {args.index}"
            
        return [{'type': 'text', 'text': f'{message}:\n{formatted_result}'}]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error getting cluster state: {str(e)}'}]


async def get_segments_tool(args: GetSegmentsArgs) -> list[dict]:
    """Tool to get information about Lucene segments in indices.
    
    Args:
        args: GetSegmentsArgs containing optional index filter
        
    Returns:
        list[dict]: Segment information in MCP format
    """
    try:
        check_tool_compatibility('GetSegmentsTool', args)
        result = get_segments(args)
        
        if isinstance(result, dict) and 'error' in result:
            return [{'type': 'text', 'text': f'Error getting segments: {result["error"]}'}]
        
        # Create a formatted table for better readability
        formatted_text = 'index | shard | prirep | segment | generation | docs.count | docs.deleted | size | memory.bookkeeping | memory.vectors | memory.docvalues | memory.terms | version\n'
        
        # Format each segment row
        for segment in result:
            formatted_text += f'{segment.get("index", "N/A")} | '
            formatted_text += f'{segment.get("shard", "N/A")} | '
            formatted_text += f'{segment.get("prirep", "N/A")} | '
            formatted_text += f'{segment.get("segment", "N/A")} | '
            formatted_text += f'{segment.get("generation", "N/A")} | '
            formatted_text += f'{segment.get("docs.count", "N/A")} | '
            formatted_text += f'{segment.get("docs.deleted", "N/A")} | '
            formatted_text += f'{segment.get("size", "N/A")} | '
            formatted_text += f'{segment.get("memory.bookkeeping", "N/A")} | '
            formatted_text += f'{segment.get("memory.vectors", "N/A")} | '
            formatted_text += f'{segment.get("memory.docvalues", "N/A")} | '
            formatted_text += f'{segment.get("memory.terms", "N/A")} | '
            formatted_text += f'{segment.get("version", "N/A")}\n'
        
        # Create response message based on what was requested
        message = "Segment information"
        if args.index:
            message += f" for index: {args.index}"
        else:
            message += " for all indices"
            
        return [{'type': 'text', 'text': f'{message}:\n{formatted_text}'}]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error getting segment information: {str(e)}'}]


async def cat_nodes_tool(args: CatNodesArgs) -> list[dict]:
    """Tool to get information about nodes in the cluster.
    
    Args:
        args: CatNodesArgs containing optional metrics filter
        
    Returns:
        list[dict]: Node information in MCP format
    """
    try:
        check_tool_compatibility('CatNodesTool', args)
        result = get_nodes(args)
        
        if isinstance(result, dict) and 'error' in result:
            return [{'type': 'text', 'text': f'Error getting nodes: {result["error"]}'}]
        
        # If no nodes found
        if not result:
            return [{'type': 'text', 'text': 'No nodes found in the cluster.'}]
        
        # Get all available columns from the first node
        columns = list(result[0].keys())
        
        # Create a formatted table header
        formatted_text = ' | '.join(columns) + '\n'
        
        # Format each node row
        for node in result:
            row_values = []
            for col in columns:
                row_values.append(str(node.get(col, 'N/A')))
            formatted_text += ' | '.join(row_values) + '\n'
        
        # Create response message based on what was requested
        message = "Node information for the cluster"
        if args.metrics:
            message += f" (metrics: {args.metrics})"
            
        return [{'type': 'text', 'text': f'{message}:\n{formatted_text}'}]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error getting node information: {str(e)}'}]


async def get_index_info_tool(args: GetIndexInfoArgs) -> list[dict]:
    """Tool to get detailed information about an index including mappings, settings, and aliases.
    
    Args:
        args: GetIndexInfoArgs containing the index name
        
    Returns:
        list[dict]: Index information in MCP format
    """
    try:
        check_tool_compatibility('GetIndexInfoTool', args)
        result = get_index_info(args)
        
        # Format the response for better readability
        formatted_result = json.dumps(result, indent=2)
        
        # Create response message
        message = f"Detailed information for index: {args.index}"
        
        return [{'type': 'text', 'text': f'{message}:\n{formatted_result}'}]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error getting index information: {str(e)}'}]


async def get_index_stats_tool(args: GetIndexStatsArgs) -> list[dict]:
    """Tool to get statistics about an index.
    
    Args:
        args: GetIndexStatsArgs containing the index name and optional metric filter
        
    Returns:
        list[dict]: Index statistics in MCP format
    """
    try:
        check_tool_compatibility('GetIndexStatsTool', args)
        result = get_index_stats(args)
        
        # Format the response for better readability
        formatted_result = json.dumps(result, indent=2)
        
        # Create response message based on what was requested
        message = f"Statistics for index: {args.index}"
        if args.metric:
            message += f" (metrics: {args.metric})"
        
        return [{'type': 'text', 'text': f'{message}:\n{formatted_result}'}]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error getting index statistics: {str(e)}'}]


async def get_query_insights_tool(args: GetQueryInsightsArgs) -> list[dict]:
    """Tool to get query insights from the /_insights/top_queries endpoint.
    
    Args:
        args: GetQueryInsightsArgs containing connection parameters
        
    Returns:
        list[dict]: Query insights in MCP format
    """
    try:
        check_tool_compatibility('GetQueryInsightsTool', args)
        result = get_query_insights(args)
        
        # Format the response for better readability
        formatted_result = json.dumps(result, indent=2)
        
        # Create simple response message
        message = "Query insights from /_insights/top_queries endpoint"
        
        return [{'type': 'text', 'text': f'{message}:\n{formatted_result}'}]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error getting query insights: {str(e)}'}]


async def get_nodes_hot_threads_tool(args: GetNodesHotThreadsArgs) -> list[dict]:
    """Tool to get information about hot threads in the cluster nodes.
    
    Args:
        args: GetNodesHotThreadsArgs containing connection parameters
        
    Returns:
        list[dict]: Hot threads information in MCP format
    """
    try:
        check_tool_compatibility('GetNodesHotThreadsTool', args)
        result = get_nodes_hot_threads(args)
        
        # Create simple response message
        message = "Hot threads information from /_nodes/hot_threads endpoint"
        
        # The hot_threads API returns text, not JSON, so we don't need to format it
        return [{'type': 'text', 'text': f'{message}:\n{result}'}]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error getting hot threads information: {str(e)}'}]


async def get_allocation_tool(args: GetAllocationArgs) -> list[dict]:
    """Tool to get information about shard allocation across nodes in the cluster.
    
    Args:
        args: GetAllocationArgs containing connection parameters
        
    Returns:
        list[dict]: Allocation information in MCP format
    """
    try:
        check_tool_compatibility('GetAllocationTool', args)
        result = get_allocation(args)
        
        if isinstance(result, dict) and 'error' in result:
            return [{'type': 'text', 'text': f'Error getting allocation information: {result["error"]}'}]
        
        # If no allocation information found
        if not result:
            return [{'type': 'text', 'text': 'No allocation information found in the cluster.'}]
        
        # Get all available columns from the first allocation entry
        columns = list(result[0].keys())
        
        # Create a formatted table header
        formatted_text = ' | '.join(columns) + '\n'
        
        # Format each allocation row
        for allocation in result:
            row_values = []
            for col in columns:
                row_values.append(str(allocation.get(col, 'N/A')))
            formatted_text += ' | '.join(row_values) + '\n'
        
        # Create simple response message
        message = "Allocation information from /_cat/allocation endpoint"
        
        return [{'type': 'text', 'text': f'{message}:\n{formatted_text}'}]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error getting allocation information: {str(e)}'}]


async def get_nodes_tool(args: GetNodesArgs) -> list[dict]:
    """Tool to get detailed information about nodes in the cluster.
    
    Args:
        args: GetNodesArgs containing optional node_id, metric filters, and other parameters
        
    Returns:
        list[dict]: Detailed node information in MCP format
    """
    try:
        check_tool_compatibility('GetNodesTool', args)
        result = get_nodes_info(args)
        
        if isinstance(result, dict) and 'error' in result:
            return [{'type': 'text', 'text': f'Error getting nodes information: {result["error"]}'}]
        
        # Format the response for better readability
        formatted_result = json.dumps(result, indent=2)
        
        # Create response message based on what was requested
        message = "Detailed node information"
        if args.node_id:
            message += f" for nodes: {args.node_id}"
        else:
            message += " for all nodes"
        
        if args.metric:
            message += f" (metrics: {args.metric})"
        
        return [{'type': 'text', 'text': f'{message}:\n{formatted_result}'}]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error getting nodes information: {str(e)}'}]


async def get_long_running_tasks_tool(args: GetLongRunningTasksArgs) -> list[dict]:
    """Tool to get information about long-running tasks in the cluster, sorted by running time.
    
    Args:
        args: GetLongRunningTasksArgs containing limit parameter
        
    Returns:
        list[dict]: Long-running tasks information in MCP format
    """
    try:
        check_tool_compatibility('GetLongRunningTasksTool', args)
        result = get_long_running_tasks(args)
        
        if isinstance(result, dict) and 'error' in result:
            return [{'type': 'text', 'text': f'Error getting long-running tasks: {result["error"]}'}]
        
        # If no tasks found
        if not result:
            return [{'type': 'text', 'text': 'No tasks found in the cluster.'}]
        
        # Get all available columns from the first task entry
        columns = list(result[0].keys())
        
        # Create a formatted table header
        formatted_text = ' | '.join(columns) + '\n'
        
        # Format each task row
        for task in result:
            row_values = []
            for col in columns:
                row_values.append(str(task.get(col, 'N/A')))
            formatted_text += ' | '.join(row_values) + '\n'
        
        # Create response message based on what was requested
        message = f"Top {len(result)} long-running tasks sorted by running time"
        
        return [{'type': 'text', 'text': f'{message}:\n{formatted_text}'}]
    except Exception as e:
        return [{'type': 'text', 'text': f'Error getting long-running tasks information: {str(e)}'}]


from .generic_api_tool import GenericOpenSearchApiArgs, generic_opensearch_api_tool


# Registry of available OpenSearch tools with their metadata
TOOL_REGISTRY = {
    'ListIndexTool': {
        'display_name': 'ListIndexTool',
        'description': 'Lists indices in the OpenSearch cluster. By default, returns a filtered list of index names only to minimize response size. Set include_detail=true to return full metadata from cat.indices (docs.count, store.size, etc.). If an index parameter is provided, returns detailed information for that specific index including mappings and settings.',
        'input_schema': ListIndicesArgs.model_json_schema(),
        'function': list_indices_tool,
        'args_model': ListIndicesArgs,
        'min_version': '1.0.0',
        'http_methods': 'GET',
    },
    'IndexMappingTool': {
        'display_name': 'IndexMappingTool',
        'description': 'Retrieves index mapping and setting information for an index in OpenSearch',
        'input_schema': GetIndexMappingArgs.model_json_schema(),
        'function': get_index_mapping_tool,
        'args_model': GetIndexMappingArgs,
        'http_methods': 'GET',
    },
    'SearchIndexTool': {
        'display_name': 'SearchIndexTool',
        'description': 'Searches an index using a query written in query domain-specific language (DSL) in OpenSearch',
        'input_schema': SearchIndexArgs.model_json_schema(),
        'function': search_index_tool,
        'args_model': SearchIndexArgs,
        'http_methods': 'GET, POST',
    },
    'GetShardsTool': {
        'display_name': 'GetShardsTool',
        'description': 'Gets information about shards in OpenSearch',
        'input_schema': GetShardsArgs.model_json_schema(),
        'function': get_shards_tool,
        'args_model': GetShardsArgs,
        'http_methods': 'GET',
    },
    'GetClusterStateTool': {
        'display_name': 'GetClusterStateTool',
        'description': 'Gets the current state of the cluster including node information, index settings, and more. Can be filtered by specific metrics and indices.',
        'input_schema': GetClusterStateArgs.model_json_schema(),
        'function': get_cluster_state_tool,
        'args_model': GetClusterStateArgs,
        'min_version': '1.0.0',
        'http_methods': 'GET',
    },
    'GetSegmentsTool': {
        'display_name': 'GetSegmentsTool',
        'description': 'Gets information about Lucene segments in indices, including memory usage, document counts, and segment sizes. Can be filtered by specific indices.',
        'input_schema': GetSegmentsArgs.model_json_schema(),
        'function': get_segments_tool,
        'args_model': GetSegmentsArgs,
        'min_version': '1.0.0',
        'http_methods': 'GET',
    },
    'CatNodesTool': {
        'display_name': 'CatNodesTool',
        'description': 'Lists node-level information, including node roles and load metrics. Gets information about nodes metrics in the OpenSearch cluster, including system metrics pid, name, cluster_manager, ip, port, version, build, jdk, along with disk, heap, ram, and file_desc. Can be filtered to specific metrics.',        
        'input_schema': CatNodesArgs.model_json_schema(),
        'function': cat_nodes_tool,
        'args_model': CatNodesArgs,
        'min_version': '1.0.0',
        'http_methods': 'GET',
    },
    'GetIndexInfoTool': {
        'display_name': 'GetIndexInfoTool',
        'description': 'Gets detailed information about an index including mappings, settings, and aliases. Supports wildcards in index names.',
        'input_schema': GetIndexInfoArgs.model_json_schema(),
        'function': get_index_info_tool,
        'args_model': GetIndexInfoArgs,
        'min_version': '1.0.0',
        'http_methods': 'GET',
    },
    'GetIndexStatsTool': {
        'display_name': 'GetIndexStatsTool',
        'description': 'Gets statistics about an index including document count, store size, indexing and search performance metrics. Can be filtered to specific metrics.',
        'input_schema': GetIndexStatsArgs.model_json_schema(),
        'function': get_index_stats_tool,
        'args_model': GetIndexStatsArgs,
        'min_version': '1.0.0',
        'http_methods': 'GET',
    },
    'GetQueryInsightsTool': {
        'display_name': 'GetQueryInsightsTool',
        'description': 'Gets query insights from the /_insights/top_queries endpoint, showing information about query patterns and performance.',
        'input_schema': GetQueryInsightsArgs.model_json_schema(),
        'function': get_query_insights_tool,
        'args_model': GetQueryInsightsArgs,
        'min_version': '2.12.0',  # Query insights feature requires OpenSearch 2.12+
        'http_methods': 'GET',
    },
    'GetNodesHotThreadsTool': {
        'display_name': 'GetNodesHotThreadsTool',
        'description': 'Gets information about hot threads in the cluster nodes from the /_nodes/hot_threads endpoint.',
        'input_schema': GetNodesHotThreadsArgs.model_json_schema(),
        'function': get_nodes_hot_threads_tool,
        'args_model': GetNodesHotThreadsArgs,
        'min_version': '1.0.0',
        'http_methods': 'GET',
    },
    'GetAllocationTool': {
        'display_name': 'GetAllocationTool',
        'description': 'Gets information about shard allocation across nodes in the cluster from the /_cat/allocation endpoint.',
        'input_schema': GetAllocationArgs.model_json_schema(),
        'function': get_allocation_tool,
        'args_model': GetAllocationArgs,
        'min_version': '1.0.0',
        'http_methods': 'GET',
    },
    'GetLongRunningTasksTool': {
        'display_name': 'GetLongRunningTasksTool',
        'description': 'Gets information about long-running tasks in the cluster, sorted by running time in descending order.',
        'input_schema': GetLongRunningTasksArgs.model_json_schema(),
        'function': get_long_running_tasks_tool,
        'args_model': GetLongRunningTasksArgs,
        'min_version': '1.0.0',
        'http_methods': 'GET',
    },
    'GetNodesTool': {
        'display_name': 'GetNodesTool',
        'description': 'Gets detailed information about nodes in the OpenSearch cluster, including static information like host system details, JVM info, processor type, node settings, thread pools, installed plugins, and more. Can be filtered by specific nodes and metrics.',
        'input_schema': GetNodesArgs.model_json_schema(),
        'function': get_nodes_tool,
        'args_model': GetNodesArgs,
        'min_version': '1.0.0',
        'http_methods': 'GET',
    },
    'GenericOpenSearchApiTool': {
        'display_name': 'GenericOpenSearchApiTool',
        'description': 'A flexible tool for calling any OpenSearch API endpoint. Supports all HTTP methods with custom paths, query parameters, request bodies, and headers. Use this when you need to access OpenSearch APIs that don\'t have dedicated tools, or when you need more control over the request. Leverages your knowledge of OpenSearch API documentation to construct appropriate requests.',
        'input_schema': GenericOpenSearchApiArgs.model_json_schema(),
        'function': generic_opensearch_api_tool,
        'args_model': GenericOpenSearchApiArgs,
        'min_version': '1.0.0',
        'http_methods': 'GET, POST, PUT, DELETE, HEAD, PATCH',
    },
}
