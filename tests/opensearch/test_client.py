# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

import boto3
import os
import pytest
from opensearch.client import initialize_client, ConfigurationError, AuthenticationError, BufferedAsyncHttpConnection
from opensearchpy import AsyncOpenSearch, AsyncHttpConnection, AWSV4SignerAsyncAuth
from tools.tool_params import baseToolArgs
from unittest.mock import Mock, patch


class TestOpenSearchClient:
    def setup_method(self):
        """Setup that runs before each test method."""
        # Clear any existing environment variables
        self.original_env = {}
        for key in [
            'OPENSEARCH_USERNAME',
            'OPENSEARCH_PASSWORD',
            'AWS_REGION',
            'OPENSEARCH_URL',
            'OPENSEARCH_NO_AUTH',
            'OPENSEARCH_SSL_VERIFY',
            'OPENSEARCH_TIMEOUT',
            'AWS_IAM_ARN',
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'AWS_SESSION_TOKEN',
        ]:
            if key in os.environ:
                self.original_env[key] = os.environ[key]
                del os.environ[key]

    def setup_method(self):
        """Setup before each test method."""
        # Clear environment variables to ensure clean test state
        for key in [
            'OPENSEARCH_USERNAME',
            'OPENSEARCH_PASSWORD',
            'AWS_REGION',
            'OPENSEARCH_URL',
            'OPENSEARCH_NO_AUTH',
            'OPENSEARCH_SSL_VERIFY',
            'OPENSEARCH_TIMEOUT',
            'AWS_IAM_ARN',
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'AWS_SESSION_TOKEN',
        ]:
            if key in os.environ:
                del os.environ[key]

        # Set global mode for tests
        from mcp_server_opensearch.global_state import set_mode

        set_mode('single')

    def teardown_method(self):
        """Cleanup after each test method."""
        # Restore original environment variables
        if hasattr(self, 'original_env'):
            for key, value in self.original_env.items():
                os.environ[key] = value

    def test_initialize_client_empty_url(self):
        """Test that initialize_client raises ConfigurationError when opensearch_url is empty."""
        with pytest.raises(ConfigurationError) as exc_info:
            initialize_client(baseToolArgs(opensearch_cluster_name=''))

        assert 'OPENSEARCH_URL environment variable is required but not set' in str(exc_info.value)

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_single_mode')
    def test_initialize_client_basic_auth(self, mock_get_region, mock_opensearch):
        """Test client initialization with basic authentication."""
        # Set environment variables
        os.environ['OPENSEARCH_USERNAME'] = 'test-user'
        os.environ['OPENSEARCH_PASSWORD'] = 'test-password'
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'

        # Mock AWS region (not needed for basic auth, but called anyway)
        mock_get_region.return_value = 'us-east-1'

        # Mock OpenSearch client
        mock_client = Mock()
        mock_opensearch.return_value = mock_client

        # Execute
        client = initialize_client(baseToolArgs(opensearch_cluster_name=''))

        # Assert
        assert client == mock_client
        mock_opensearch.assert_called_once_with(
            hosts=['https://test-opensearch-domain.com'],
            use_ssl=True,
            verify_certs=True,
            connection_class=BufferedAsyncHttpConnection,
            timeout=30,
            max_response_size=None,  # No limit by default
            http_auth=('test-user', 'test-password'),
        )

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.boto3.Session')
    def test_initialize_client_aws_auth(self, mock_session, mock_opensearch):
        """Test client initialization with AWS IAM authentication."""
        # Set environment variables (no basic auth to allow AWS auth)
        os.environ['AWS_REGION'] = 'us-west-2'
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'
        # Clear any basic auth env vars
        if 'OPENSEARCH_USERNAME' in os.environ:
            del os.environ['OPENSEARCH_USERNAME']
        if 'OPENSEARCH_PASSWORD' in os.environ:
            del os.environ['OPENSEARCH_PASSWORD']

        # Mock AWS credentials
        mock_credentials = Mock()
        mock_credentials.access_key = 'test-access-key'
        mock_credentials.secret_key = 'test-secret-key'
        mock_credentials.token = 'test-token'

        mock_session_instance = Mock()
        mock_session_instance.get_credentials.return_value = mock_credentials
        mock_session.return_value = mock_session_instance

        # Mock OpenSearch client
        mock_client = Mock()
        mock_opensearch.return_value = mock_client

        # Execute
        client = initialize_client(baseToolArgs(opensearch_cluster_name=''))

        # Assert
        assert client == mock_client
        mock_opensearch.assert_called_once()
        call_kwargs = mock_opensearch.call_args[1]
        assert call_kwargs['hosts'] == ['https://test-opensearch-domain.com']
        assert call_kwargs['use_ssl'] is True
        assert call_kwargs['verify_certs'] is True
        assert call_kwargs['connection_class'] == BufferedAsyncHttpConnection
        assert call_kwargs['max_response_size'] is None  # No limit by default
        assert isinstance(call_kwargs['http_auth'], AWSV4SignerAsyncAuth)

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.boto3.Session')
    def test_initialize_client_aws_auth_error(self, mock_session, mock_opensearch):
        """Test client initialization when AWS authentication fails."""
        # Set environment variables
        os.environ['AWS_REGION'] = 'us-west-2'
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'

        # Mock AWS session to raise an error
        mock_session_instance = Mock()
        mock_session_instance.get_credentials.side_effect = boto3.exceptions.Boto3Error(
            'AWS credentials error'
        )
        mock_session.return_value = mock_session_instance

        # Execute and assert
        with pytest.raises(AuthenticationError) as exc_info:
            initialize_client(baseToolArgs(opensearch_cluster_name=''))
        assert 'Failed to authenticate with AWS credentials' in str(exc_info.value)

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.boto3.Session')
    def test_initialize_client_no_auth(self, mock_session, mock_opensearch):
        """Test client initialization when no authentication is available."""
        # Set environment variable
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'

        # Mock AWS session to return no credentials
        mock_session_instance = Mock()
        mock_session_instance.get_credentials.return_value = None
        mock_session.return_value = mock_session_instance

        # Execute and assert
        with pytest.raises(AuthenticationError) as exc_info:
            initialize_client(baseToolArgs(opensearch_cluster_name=''))
        assert 'No AWS credentials found in session' in str(exc_info.value)

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_single_mode')
    def test_initialize_client_no_auth_enabled(self, mock_get_region, mock_opensearch):
        """Test client initialization with OPENSEARCH_NO_AUTH=true."""
        # Set environment variables
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'
        os.environ['OPENSEARCH_NO_AUTH'] = 'true'

        # Mock AWS region (not needed for no auth, but called anyway)
        mock_get_region.return_value = 'us-east-1'

        # Mock OpenSearch client
        mock_client = Mock()
        mock_opensearch.return_value = mock_client

        # Execute
        client = initialize_client(baseToolArgs(opensearch_cluster_name=''))

        # Assert
        assert client == mock_client
        mock_opensearch.assert_called_once_with(
            hosts=['https://test-opensearch-domain.com'],
            use_ssl=True,
            verify_certs=True,
            connection_class=BufferedAsyncHttpConnection,
            timeout=30,
            max_response_size=None,  # No limit by default
        )

    @patch('opensearch.client._initialize_client_single_mode')
    def test_initialize_client_with_timeout_env(self, mock_init):
        """Test client initialization with timeout from environment."""
        os.environ['OPENSEARCH_TIMEOUT'] = '30'
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'
        os.environ['OPENSEARCH_USERNAME'] = 'admin'
        os.environ['OPENSEARCH_PASSWORD'] = 'password'

        mock_client = Mock()
        mock_init.return_value = mock_client

        client = initialize_client(baseToolArgs(opensearch_cluster_name=''))
        assert client == mock_client

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_multi_mode')
    def test__initialize_client_multi_mode_timeout(self, mock_get_region, mock_opensearch):
        """Test client initialization with cluster timeout."""
        from mcp_server_opensearch.clusters_information import ClusterInfo
        from opensearch.client import _initialize_client_multi_mode

        cluster_info = ClusterInfo(
            opensearch_url='https://localhost:9200',
            opensearch_username='admin',
            opensearch_password='password',
            timeout=60,
        )

        # Mock AWS region (not needed for basic auth, but called anyway)
        mock_get_region.return_value = 'us-east-1'

        mock_client = Mock()
        mock_opensearch.return_value = mock_client

        client = _initialize_client_multi_mode(cluster_info)

        assert client == mock_client
        call_kwargs = mock_opensearch.call_args[1]
        assert call_kwargs['timeout'] == 60

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_multi_mode')
    def test__initialize_client_multi_mode_no_auth(self, mock_get_region, mock_opensearch):
        """Test client initialization with no-auth from cluster config."""
        from mcp_server_opensearch.clusters_information import ClusterInfo
        from opensearch.client import _initialize_client_multi_mode

        cluster_info = ClusterInfo(
            opensearch_url='http://localhost:9200',
            opensearch_no_auth=True,
        )

        # Mock AWS region (not needed for no auth, but called anyway)
        mock_get_region.return_value = 'us-east-1'

        mock_client = Mock()
        mock_opensearch.return_value = mock_client

        client = _initialize_client_multi_mode(cluster_info)

        assert client == mock_client
        call_kwargs = mock_opensearch.call_args[1]
        assert call_kwargs['hosts'] == ['http://localhost:9200']
        assert call_kwargs['use_ssl'] is False  # http:// URL
        assert call_kwargs['verify_certs'] is True
        assert call_kwargs['connection_class'] == BufferedAsyncHttpConnection
        assert call_kwargs['max_response_size'] is None  # No limit by default
        # Should not have http_auth when no-auth is True
        assert 'http_auth' not in call_kwargs

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_multi_mode')
    def test_initialize_client_no_auth_priority_cluster_over_env(
        self, mock_get_region, mock_opensearch
    ):
        """Test that cluster config opensearch_no_auth takes priority over environment variable."""
        from mcp_server_opensearch.clusters_information import ClusterInfo
        from opensearch.client import _initialize_client_multi_mode

        # Set environment variable to false
        os.environ['OPENSEARCH_NO_AUTH'] = 'false'

        cluster_info = ClusterInfo(
            opensearch_url='http://localhost:9200',
            opensearch_no_auth=True,  # Cluster config says no auth
        )

        # Mock AWS region (not needed for no auth, but called anyway)
        mock_get_region.return_value = 'us-east-1'

        mock_client = Mock()
        mock_opensearch.return_value = mock_client

        client = _initialize_client_multi_mode(cluster_info)

        assert client == mock_client
        call_kwargs = mock_opensearch.call_args[1]
        # Should use no auth because cluster config takes priority
        assert 'http_auth' not in call_kwargs

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_cluster')
    @patch('opensearch.client.get_aws_region_multi_mode')
    def test_initialize_client_multi_cluster_no_auth(
        self, mock_get_region, mock_get_cluster, mock_opensearch
    ):
        """Test client initialization in multi-cluster mode with no-auth cluster."""
        from mcp_server_opensearch.clusters_information import ClusterInfo
        from mcp_server_opensearch.global_state import set_mode

        # Set mode to multi for this test
        set_mode('multi')

        # Mock cluster info with no-auth
        cluster_info = ClusterInfo(
            opensearch_url='http://localhost:9200',
            opensearch_no_auth=True,
        )
        mock_get_cluster.return_value = cluster_info

        # Mock AWS region (not needed for no auth, but called anyway)
        mock_get_region.return_value = 'us-east-1'

        # Mock OpenSearch client
        mock_client = Mock()
        mock_opensearch.return_value = mock_client

        # Create args with cluster name
        args = baseToolArgs(opensearch_cluster_name='')
        args.opensearch_cluster_name = 'no-auth-cluster'

        client = initialize_client(args)

        assert client == mock_client
        mock_get_cluster.assert_called_once_with('no-auth-cluster')
        call_kwargs = mock_opensearch.call_args[1]
        assert call_kwargs['hosts'] == ['http://localhost:9200']
        assert call_kwargs['use_ssl'] is False
        assert 'http_auth' not in call_kwargs


class TestOpenSearchClientContextManager:
    """Tests for the get_opensearch_client() async context manager."""

    def setup_method(self):
        """Setup before each test method."""
        # Clear environment variables to ensure clean test state
        for key in [
            'OPENSEARCH_USERNAME',
            'OPENSEARCH_PASSWORD',
            'AWS_REGION',
            'OPENSEARCH_URL',
            'OPENSEARCH_NO_AUTH',
            'OPENSEARCH_SSL_VERIFY',
            'OPENSEARCH_TIMEOUT',
            'AWS_IAM_ARN',
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'AWS_SESSION_TOKEN',
        ]:
            if key in os.environ:
                del os.environ[key]

        # Set global mode for tests
        from mcp_server_opensearch.global_state import set_mode

        set_mode('single')

    @pytest.mark.asyncio
    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_single_mode')
    async def test_context_manager_successful_creation_and_cleanup(
        self, mock_get_region, mock_opensearch
    ):
        """Test that context manager creates client and calls close() on exit."""
        from opensearch.client import get_opensearch_client

        # Set environment variables
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'
        os.environ['OPENSEARCH_USERNAME'] = 'test-user'
        os.environ['OPENSEARCH_PASSWORD'] = 'test-password'

        # Mock AWS region
        mock_get_region.return_value = 'us-east-1'

        # Mock OpenSearch client with close method
        mock_client = Mock()
        mock_client.close = Mock(return_value=None)
        mock_opensearch.return_value = mock_client

        # Use context manager
        async with get_opensearch_client(baseToolArgs(opensearch_cluster_name='')) as client:
            assert client == mock_client

        # Verify close was called
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_single_mode')
    async def test_context_manager_cleanup_on_exception(self, mock_get_region, mock_opensearch):
        """Test that context manager calls close() even when exception occurs."""
        from opensearch.client import get_opensearch_client

        # Set environment variables
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'
        os.environ['OPENSEARCH_USERNAME'] = 'test-user'
        os.environ['OPENSEARCH_PASSWORD'] = 'test-password'

        # Mock AWS region
        mock_get_region.return_value = 'us-east-1'

        # Mock OpenSearch client with close method
        mock_client = Mock()
        mock_client.close = Mock(return_value=None)
        mock_opensearch.return_value = mock_client

        # Use context manager and raise exception
        with pytest.raises(RuntimeError):
            async with get_opensearch_client(baseToolArgs(opensearch_cluster_name='')) as client:
                assert client == mock_client
                raise RuntimeError('Test exception')

        # Verify close was still called
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_single_mode')
    async def test_context_manager_cleanup_error_logged_not_propagated(
        self, mock_get_region, mock_opensearch
    ):
        """Test that cleanup errors are logged but not propagated."""
        from opensearch.client import get_opensearch_client

        # Set environment variables
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'
        os.environ['OPENSEARCH_USERNAME'] = 'test-user'
        os.environ['OPENSEARCH_PASSWORD'] = 'test-password'

        # Mock AWS region
        mock_get_region.return_value = 'us-east-1'

        # Mock OpenSearch client with close method that raises exception
        mock_client = Mock()
        mock_client.close = Mock(side_effect=Exception('Cleanup error'))
        mock_opensearch.return_value = mock_client

        # Use context manager - should not raise cleanup exception
        async with get_opensearch_client(baseToolArgs(opensearch_cluster_name='')) as client:
            assert client == mock_client

        # Verify close was called
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_single_mode')
    async def test_context_manager_cleanup_error_does_not_mask_original_exception(
        self, mock_get_region, mock_opensearch
    ):
        """Test that cleanup errors don't mask the original exception."""
        from opensearch.client import get_opensearch_client

        # Set environment variables
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'
        os.environ['OPENSEARCH_USERNAME'] = 'test-user'
        os.environ['OPENSEARCH_PASSWORD'] = 'test-password'

        # Mock AWS region
        mock_get_region.return_value = 'us-east-1'

        # Mock OpenSearch client with close method that raises exception
        mock_client = Mock()
        mock_client.close = Mock(side_effect=Exception('Cleanup error'))
        mock_opensearch.return_value = mock_client

        # Use context manager and raise exception - should get original exception
        with pytest.raises(RuntimeError, match='Original exception'):
            async with get_opensearch_client(baseToolArgs(opensearch_cluster_name='')) as client:
                assert client == mock_client
                raise RuntimeError('Original exception')

        # Verify close was still called
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_single_mode')
    async def test_context_manager_multiple_sequential_calls(
        self, mock_get_region, mock_opensearch
    ):
        """Test that multiple sequential context manager calls each create and close clients."""
        from opensearch.client import get_opensearch_client

        # Set environment variables
        os.environ['OPENSEARCH_URL'] = 'https://test-opensearch-domain.com'
        os.environ['OPENSEARCH_USERNAME'] = 'test-user'
        os.environ['OPENSEARCH_PASSWORD'] = 'test-password'

        # Mock AWS region
        mock_get_region.return_value = 'us-east-1'

        # Mock OpenSearch clients
        mock_client1 = Mock()
        mock_client1.close = Mock(return_value=None)
        mock_client2 = Mock()
        mock_client2.close = Mock(return_value=None)
        mock_client3 = Mock()
        mock_client3.close = Mock(return_value=None)

        mock_opensearch.side_effect = [mock_client1, mock_client2, mock_client3]

        # First call
        async with get_opensearch_client(baseToolArgs(opensearch_cluster_name='')) as client:
            assert client == mock_client1
        mock_client1.close.assert_called_once()

        # Second call
        async with get_opensearch_client(baseToolArgs(opensearch_cluster_name='')) as client:
            assert client == mock_client2
        mock_client2.close.assert_called_once()

        # Third call
        async with get_opensearch_client(baseToolArgs(opensearch_cluster_name='')) as client:
            assert client == mock_client3
        mock_client3.close.assert_called_once()

        # Verify all three clients were created
        assert mock_opensearch.call_count == 3
