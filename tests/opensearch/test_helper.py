# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import pytest
import json
from tools.tool_params import (
    GetIndexMappingArgs,
    GetShardsArgs,
    ListIndicesArgs,
    SearchIndexArgs,
    baseToolArgs,
)
from unittest.mock import patch, AsyncMock, MagicMock


class TestOpenSearchHelper:
    def setup_method(self):
        """Setup that runs before each test method."""
        from opensearch.helper import (
            get_index_mapping,
            get_shards,
            list_indices,
            search_index,
        )

        # Store functions
        self.list_indices = list_indices
        self.get_index_mapping = get_index_mapping
        self.search_index = search_index
        self.get_shards = get_shards

    @pytest.mark.asyncio
    @patch('opensearch.client.get_opensearch_client')
    async def test_list_indices(self, mock_get_client):
        """Test list_indices function."""
        # Setup mock response
        mock_response = [
            {'index': 'index1', 'health': 'green', 'status': 'open'},
            {'index': 'index2', 'health': 'yellow', 'status': 'open'},
        ]
        mock_client = AsyncMock()
        mock_client.cat.indices = AsyncMock(return_value=mock_response)

        # Setup async context manager
        mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute
        result = await self.list_indices(ListIndicesArgs(opensearch_cluster_name=''))

        # Assert
        assert result == mock_response
        mock_get_client.assert_called_once_with(ListIndicesArgs(opensearch_cluster_name=''))
        mock_client.cat.indices.assert_called_once_with(index=None, format='json')

    @pytest.mark.asyncio
    @patch('opensearch.client.get_opensearch_client')
    async def test_get_index_mapping(self, mock_get_client):
        """Test get_index_mapping function."""
        # Setup mock response
        mock_response = {
            'test-index': {
                'mappings': {
                    'properties': {
                        'field1': {'type': 'text'},
                        'field2': {'type': 'keyword'},
                    }
                }
            }
        }
        mock_client = AsyncMock()
        mock_client.indices.get_mapping = AsyncMock(return_value=mock_response)

        # Setup async context manager
        mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute
        result = await self.get_index_mapping(
            GetIndexMappingArgs(index='test-index', opensearch_cluster_name='')
        )

        # Assert
        assert result == mock_response
        mock_get_client.assert_called_once_with(
            GetIndexMappingArgs(index='test-index', opensearch_cluster_name='')
        )
        mock_client.indices.get_mapping.assert_called_once_with(index='test-index')

    @pytest.mark.asyncio
    @patch('opensearch.client.get_opensearch_client')
    async def test_search_index(self, mock_get_client):
        """Test search_index function."""
        # Setup mock response
        mock_response = {
            'hits': {
                'total': {'value': 1},
                'hits': [{'_index': 'test-index', '_id': '1', '_source': {'field': 'value'}}],
            }
        }
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(return_value=mock_response)

        # Setup async context manager
        mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)

        # Setup test query
        test_query = {'query': {'match_all': {}}}

        # Execute
        result = await self.search_index(
            SearchIndexArgs(index='test-index', query=test_query, opensearch_cluster_name='')
        )

        # Assert
        assert result == mock_response
        mock_get_client.assert_called_once_with(
            SearchIndexArgs(index='test-index', query=test_query, opensearch_cluster_name='')
        )
        # The search_index function adds size to the query body (default 10, max 100)
        expected_body = {'query': {'match_all': {}}, 'size': 10}
        mock_client.search.assert_called_once_with(index='test-index', body=expected_body)

    @pytest.mark.asyncio
    @patch('opensearch.client.get_opensearch_client')
    async def test_get_shards(self, mock_get_client):
        """Test get_shards function."""
        # Setup mock response
        mock_response = [
            {
                'index': 'test-index',
                'shard': '0',
                'prirep': 'p',
                'state': 'STARTED',
                'docs': '1000',
                'store': '1mb',
                'ip': '127.0.0.1',
                'node': 'node1',
            }
        ]
        mock_client = AsyncMock()
        mock_client.cat.shards = AsyncMock(return_value=mock_response)

        # Setup async context manager
        mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute
        result = await self.get_shards(
            GetShardsArgs(index='test-index', opensearch_cluster_name='')
        )

        # Assert
        assert result == mock_response
        mock_get_client.assert_called_once_with(
            GetShardsArgs(index='test-index', opensearch_cluster_name='')
        )
        mock_client.cat.shards.assert_called_once_with(index='test-index', format='json')

    @pytest.mark.asyncio
    @patch('opensearch.client.get_opensearch_client')
    async def test_list_indices_error(self, mock_get_client):
        """Test list_indices error handling."""
        # Setup mock to raise exception
        mock_client = AsyncMock()
        mock_client.cat.indices = AsyncMock(side_effect=Exception('Connection error'))

        # Setup async context manager
        mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute and assert
        with pytest.raises(Exception) as exc_info:
            await self.list_indices(ListIndicesArgs(opensearch_cluster_name=''))
        assert str(exc_info.value) == 'Connection error'

    @pytest.mark.asyncio
    @patch('opensearch.client.get_opensearch_client')
    async def test_get_index_mapping_error(self, mock_get_client):
        """Test get_index_mapping error handling."""
        # Setup mock to raise exception
        mock_client = AsyncMock()
        mock_client.indices.get_mapping = AsyncMock(side_effect=Exception('Index not found'))

        # Setup async context manager
        mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute and assert
        with pytest.raises(Exception) as exc_info:
            await self.get_index_mapping(
                GetIndexMappingArgs(index='non-existent-index', opensearch_cluster_name='')
            )
        assert str(exc_info.value) == 'Index not found'

    @pytest.mark.asyncio
    @patch('opensearch.client.get_opensearch_client')
    async def test_search_index_error(self, mock_get_client):
        """Test search_index error handling."""
        # Setup mock to raise exception
        mock_client = AsyncMock()
        mock_client.search = AsyncMock(side_effect=Exception('Invalid query'))

        # Setup async context manager
        mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute and assert
        with pytest.raises(Exception) as exc_info:
            await self.search_index(
                SearchIndexArgs(
                    index='test-index', query={'invalid': 'query'}, opensearch_cluster_name=''
                )
            )
        assert str(exc_info.value) == 'Invalid query'

    @pytest.mark.asyncio
    @patch('opensearch.client.get_opensearch_client')
    async def test_get_shards_error(self, mock_get_client):
        """Test get_shards error handling."""
        # Setup mock to raise exception
        mock_client = AsyncMock()
        mock_client.cat.shards = AsyncMock(side_effect=Exception('Shard not found'))

        # Setup async context manager
        mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute and assert
        with pytest.raises(Exception) as exc_info:
            await self.get_shards(
                GetShardsArgs(index='non-existent-index', opensearch_cluster_name='')
            )
        assert str(exc_info.value) == 'Shard not found'

    @pytest.mark.asyncio
    @patch('opensearch.client.get_opensearch_client')
    async def test_get_opensearch_version(self, mock_get_client):
        from opensearch.helper import get_opensearch_version

        # Setup mock response
        mock_response = {'version': {'number': '2.11.1'}}
        mock_client = AsyncMock()
        mock_client.info = AsyncMock(return_value=mock_response)
        mock_client.close = AsyncMock()

        # Setup async context manager
        mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)

        # Execute
        args = baseToolArgs(opensearch_cluster_name='')
        result = await get_opensearch_version(args)
        # Assert
        assert str(result) == '2.11.1'
        mock_get_client.assert_called_once_with(args)
        mock_client.info.assert_called_once_with()

    @pytest.mark.asyncio
    @patch('opensearch.client.get_opensearch_client')
    async def test_get_opensearch_version_error(self, mock_get_client):
        from opensearch.helper import get_opensearch_version
        from tools.tool_params import baseToolArgs

        # Setup mock to raise exception
        mock_client = AsyncMock()
        mock_client.info = AsyncMock(side_effect=Exception('Failed to get version'))
        mock_client.close = AsyncMock()

        # Setup async context manager
        mock_get_client.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_get_client.return_value.__aexit__ = AsyncMock(return_value=None)

        args = baseToolArgs(opensearch_cluster_name='')
        # Execute and assert
        result = await get_opensearch_version(args)
        assert result is None
        
    def test_convert_search_results_to_csv_hits_only(self):
        """Test convert_search_results_to_csv with hits only."""
        import importlib.util
        import os
        spec = importlib.util.spec_from_file_location("helper", os.path.join(os.path.dirname(__file__), '../../src/opensearch/helper.py'))
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        convert_search_results_to_csv = helper.convert_search_results_to_csv
        
        search_results = {
            "hits": {
                "total": {"value": 2, "relation": "eq"},
                "hits": [
                    {
                        "_index": "products",
                        "_id": "1",
                        "_score": 1.5,
                        "_source": {
                            "name": "Laptop",
                            "price": 999.99,
                            "category": "electronics"
                        }
                    },
                    {
                        "_index": "products",
                        "_id": "2",
                        "_score": 1.2,
                        "_source": {
                            "name": "Phone",
                            "price": 599.99,
                            "category": "electronics"
                        }
                    }
                ]
            }
        }
        
        result = convert_search_results_to_csv(search_results)
        assert "_id,_index,_score,category,name,price" in result
        assert "1,products,1.5,electronics,Laptop,999.99" in result
        assert "2,products,1.2,electronics,Phone,599.99" in result

    def test_convert_search_results_to_csv_aggregations_only(self):
        """Test convert_search_results_to_csv with aggregations only."""
        import importlib.util
        import os
        spec = importlib.util.spec_from_file_location("helper", os.path.join(os.path.dirname(__file__), '../../src/opensearch/helper.py'))
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        convert_search_results_to_csv = helper.convert_search_results_to_csv
        
        search_results = {
            "hits": {"total": {"value": 100}, "hits": []},
            "aggregations": {
                "categories": {
                    "buckets": [
                        {"key": "electronics", "doc_count": 45},
                        {"key": "books", "doc_count": 30},
                        {"key": "clothing", "doc_count": 25}
                    ]
                },
                "avg_price": {
                    "value": 299.99
                }
            }
        }
        
        result = convert_search_results_to_csv(search_results)
        assert "categories" in result
        assert "avg_price" in result
        assert "electronics" in result
        assert "299.99" in result

    def test_convert_search_results_to_csv_hits_and_aggregations(self):
        """Test convert_search_results_to_csv with both hits and aggregations."""
        import importlib.util
        import os
        spec = importlib.util.spec_from_file_location("helper", os.path.join(os.path.dirname(__file__), '../../src/opensearch/helper.py'))
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        convert_search_results_to_csv = helper.convert_search_results_to_csv
        
        search_results = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_index": "products",
                        "_id": "1",
                        "_score": 1.0,
                        "_source": {
                            "name": "Laptop",
                            "price": 999.99
                        }
                    }
                ]
            },
            "aggregations": {
                "price_stats": {
                    "min": 99.99,
                    "max": 1999.99,
                    "avg": 549.99
                }
            }
        }
        
        result = convert_search_results_to_csv(search_results)
        assert "SEARCH HITS:" in result
        assert "AGGREGATIONS:" in result
        assert "_id,_index,_score,name,price" in result
        assert "1,products,1.0,Laptop,999.99" in result
        assert "price_stats" in result
        assert "549.99" in result

    def test_convert_search_results_to_csv_nested_aggregations(self):
        """Test convert_search_results_to_csv with nested aggregations."""
        import importlib.util
        import os
        spec = importlib.util.spec_from_file_location("helper", os.path.join(os.path.dirname(__file__), '../../src/opensearch/helper.py'))
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        convert_search_results_to_csv = helper.convert_search_results_to_csv
        
        search_results = {
            "hits": {"total": {"value": 1000}, "hits": []},
            "aggregations": {
                "categories": {
                    "buckets": [
                        {
                            "key": "electronics",
                            "doc_count": 500,
                            "avg_price": {"value": 299.99},
                            "brands": {
                                "buckets": [
                                    {"key": "Apple", "doc_count": 200},
                                    {"key": "Samsung", "doc_count": 150}
                                ]
                            }
                        },
                        {
                            "key": "books",
                            "doc_count": 300,
                            "avg_price": {"value": 19.99},
                            "genres": {
                                "buckets": [
                                    {"key": "fiction", "doc_count": 180},
                                    {"key": "non-fiction", "doc_count": 120}
                                ]
                            }
                        }
                    ]
                },
                "total_revenue": {
                    "value": 125000.50
                }
            }
        }
        
        result = convert_search_results_to_csv(search_results)
        assert "categories" in result
        assert "total_revenue" in result
        assert "electronics" in result
        assert "Apple" in result
        assert "fiction" in result
        assert "125000.5" in result

    def test_convert_search_results_to_csv_nested_objects(self):
        """Test convert_search_results_to_csv with nested objects in hits."""
        import importlib.util
        import os
        spec = importlib.util.spec_from_file_location("helper", os.path.join(os.path.dirname(__file__), '../../src/opensearch/helper.py'))
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        convert_search_results_to_csv = helper.convert_search_results_to_csv
        
        search_results = {
            "hits": {
                "hits": [
                    {
                        "_index": "users",
                        "_id": "1",
                        "_score": 1.0,
                        "_source": {
                            "name": "John Doe",
                            "address": {
                                "street": "123 Main St",
                                "city": "New York",
                                "coordinates": {
                                    "lat": 40.7128,
                                    "lon": -74.0060
                                }
                            },
                            "tags": ["developer", "python"],
                            "skills": [
                                {"name": "Python", "level": "expert"},
                                {"name": "JavaScript", "level": "intermediate"}
                            ]
                        }
                    }
                ]
            }
        }
        
        result = convert_search_results_to_csv(search_results)
        # Check flattened nested fields
        assert "address.city" in result
        assert "address.coordinates.lat" in result
        assert "address.coordinates.lon" in result
        assert "New York" in result
        assert "40.7128" in result
        assert "-74.006" in result
        # Check arrays are JSON encoded (CSV escapes quotes)
        assert '"[""developer"", ""python""]"' in result

    def test_convert_search_results_to_csv_empty_results(self):
        """Test convert_search_results_to_csv with empty results."""
        import importlib.util
        import os
        spec = importlib.util.spec_from_file_location("helper", os.path.join(os.path.dirname(__file__), '../../src/opensearch/helper.py'))
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        convert_search_results_to_csv = helper.convert_search_results_to_csv
        
        # Empty search results
        assert convert_search_results_to_csv({}) == "No search results to convert"
        assert convert_search_results_to_csv(None) == "No search results to convert"
        
        # No hits
        search_results = {"hits": {"hits": []}}
        result = convert_search_results_to_csv(search_results)
        assert "No search results to convert" in result
        
        # Only aggregations with empty hits
        search_results = {
            "hits": {"hits": []},
            "aggregations": {"count": {"value": 0}}
        }
        result = convert_search_results_to_csv(search_results)
        assert "count" in result
        assert "0" in result

    def test_normalize_scientific_notation(self):
        import importlib.util
        import os
        spec = importlib.util.spec_from_file_location("helper", os.path.join(os.path.dirname(__file__),
                                                                             '../../src/opensearch/helper.py'))
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        normalize_scientific_notation = helper.normalize_scientific_notation
        query_dsl = {
            "query": {
                "range": {
                    "timestamp": {
                        "gte": 1732693003E+3,
                        "lte": 173.5
                    }
                }
            }
        }
        result = normalize_scientific_notation(query_dsl)
        assert "1732693003000" in json.dumps(result)
        assert "173.5" in json.dumps(result)
