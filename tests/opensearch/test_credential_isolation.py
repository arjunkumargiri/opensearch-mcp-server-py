# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""Tests for credential isolation and dynamic mode security guards.

These tests verify that:
1. When opensearch_url is provided dynamically, the client is built entirely
   from per-call args — no env-sourced credentials are inherited.
2. URL overrides are rejected entirely when dynamic connection mode is disabled.
3. Header-auth URL overrides also build from header values only.
"""

import os
import pytest
from opensearch.client import (
    ConfigurationError,
    initialize_client,
)
from tools.tool_params import baseToolArgs
from unittest.mock import Mock, patch


class TestCredentialIsolation:
    """Tests that env credentials are NOT leaked to untrusted dynamic URLs."""

    def setup_method(self):
        self.original_env = {}
        self._env_keys = [
            'OPENSEARCH_URL',
            'OPENSEARCH_USERNAME',
            'OPENSEARCH_PASSWORD',
            'OPENSEARCH_NO_AUTH',
            'AWS_IAM_ARN',
            'AWS_REGION',
            'AWS_PROFILE',
            'AWS_OPENSEARCH_SERVERLESS',
            'OPENSEARCH_HEADER_AUTH',
            'OPENSEARCH_TIMEOUT',
            'OPENSEARCH_SSL_VERIFY',
            'OPENSEARCH_MAX_RESPONSE_SIZE',
            'OPENSEARCH_DYNAMIC_CONNECTION',
            'OPENSEARCH_ALLOWED_URLS',
        ]
        for key in self._env_keys:
            if key in os.environ:
                self.original_env[key] = os.environ[key]
                del os.environ[key]

        from mcp_server_opensearch.global_state import set_mode

        set_mode('single')

    def teardown_method(self):
        for key in self._env_keys:
            os.environ.pop(key, None)
        for key, value in self.original_env.items():
            os.environ[key] = value

    @patch('opensearch.client.get_aws_region_single_mode')
    @patch('opensearch.client.is_dynamic_mode_enabled', return_value=True)
    def test_dynamic_url_rejected_without_allowlist(
        self, mock_dynamic, mock_get_region
    ):
        """Dynamic URL without allowlist raises ConfigurationError."""
        os.environ['OPENSEARCH_URL'] = 'https://prod-cluster.example.com:9200'
        os.environ['OPENSEARCH_USERNAME'] = 'admin'
        os.environ['OPENSEARCH_PASSWORD'] = 'supersecret'
        mock_get_region.return_value = 'us-east-1'

        args = baseToolArgs(
            opensearch_cluster_name='',
            opensearch_url='https://attacker.evil.com:9200',
        )
        with pytest.raises(ConfigurationError, match='OPENSEARCH_ALLOWED_URLS'):
            initialize_client(args)

    @patch('opensearch.client.get_aws_region_single_mode')
    @patch('opensearch.client.is_dynamic_mode_enabled', return_value=True)
    def test_localhost_ssrf_rejected_without_allowlist(
        self, mock_dynamic, mock_get_region
    ):
        """SSRF to localhost rejected without allowlist."""
        os.environ['OPENSEARCH_URL'] = 'https://prod-cluster.example.com:9200'
        os.environ['OPENSEARCH_USERNAME'] = 'admin'
        os.environ['OPENSEARCH_PASSWORD'] = 'supersecret'
        mock_get_region.return_value = 'us-east-1'

        args = baseToolArgs(
            opensearch_cluster_name='',
            opensearch_url='http://127.0.0.1:8899',
        )
        with pytest.raises(ConfigurationError, match='OPENSEARCH_ALLOWED_URLS'):
            initialize_client(args)

    @patch('opensearch.client.get_aws_region_single_mode')
    @patch('opensearch.client.is_dynamic_mode_enabled', return_value=True)
    def test_disallowed_url_rejected_even_with_per_call_creds(
        self, mock_dynamic, mock_get_region
    ):
        """Even with per-call creds, non-allowlisted URL is rejected."""
        os.environ['OPENSEARCH_URL'] = 'https://prod-cluster.example.com:9200'
        os.environ['OPENSEARCH_ALLOWED_URLS'] = 'https://trusted.example.com:9200'
        mock_get_region.return_value = 'us-east-1'

        args = baseToolArgs(
            opensearch_cluster_name='',
            opensearch_url='https://attacker.evil.com:9200',
            opensearch_username='attacker-user',
            opensearch_password='attacker-pass',
        )
        with pytest.raises(ConfigurationError, match='not in the allowed URLs list'):
            initialize_client(args)

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_single_mode')
    @patch('opensearch.client.is_dynamic_mode_enabled', return_value=True)
    def test_allowed_url_inherits_env_creds(
        self, mock_dynamic, mock_get_region, mock_opensearch
    ):
        """Allowed URL gets env credentials (operator trusts this host)."""
        os.environ['OPENSEARCH_URL'] = 'https://prod-cluster.example.com:9200'
        os.environ['OPENSEARCH_USERNAME'] = 'admin'
        os.environ['OPENSEARCH_PASSWORD'] = 'supersecret'
        os.environ['OPENSEARCH_ALLOWED_URLS'] = 'https://other-cluster.example.com:9200'
        mock_get_region.return_value = 'us-east-1'
        mock_opensearch.return_value = Mock()

        args = baseToolArgs(
            opensearch_cluster_name='',
            opensearch_url='https://other-cluster.example.com:9200',
        )
        initialize_client(args)

        call_kwargs = mock_opensearch.call_args[1]
        assert 'other-cluster.example.com' in call_kwargs['hosts'][0]
        assert call_kwargs['http_auth'] == ('admin', 'supersecret')

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_single_mode')
    @patch('opensearch.client.is_dynamic_mode_enabled', return_value=True)
    def test_allowed_url_per_call_creds_override_env(
        self, mock_dynamic, mock_get_region, mock_opensearch
    ):
        """Per-call credentials override env when URL is in allowlist."""
        os.environ['OPENSEARCH_URL'] = 'https://prod-cluster.example.com:9200'
        os.environ['OPENSEARCH_USERNAME'] = 'admin'
        os.environ['OPENSEARCH_PASSWORD'] = 'supersecret'
        os.environ['OPENSEARCH_ALLOWED_URLS'] = 'https://other-cluster.example.com:9200'
        mock_get_region.return_value = 'us-east-1'
        mock_opensearch.return_value = Mock()

        args = baseToolArgs(
            opensearch_cluster_name='',
            opensearch_url='https://other-cluster.example.com:9200',
            opensearch_username='other-user',
            opensearch_password='other-pass',
        )
        initialize_client(args)

        call_kwargs = mock_opensearch.call_args[1]
        assert call_kwargs['http_auth'] == ('other-user', 'other-pass')

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_single_mode')
    @patch('opensearch.client.is_dynamic_mode_enabled', return_value=True)
    def test_no_url_override_uses_env_normally(
        self, mock_dynamic, mock_get_region, mock_opensearch
    ):
        """When no dynamic URL is provided, env credentials are used normally."""
        os.environ['OPENSEARCH_URL'] = 'https://prod-cluster.example.com:9200'
        os.environ['OPENSEARCH_USERNAME'] = 'admin'
        os.environ['OPENSEARCH_PASSWORD'] = 'supersecret'
        mock_get_region.return_value = 'us-east-1'
        mock_opensearch.return_value = Mock()

        args = baseToolArgs(opensearch_cluster_name='')
        initialize_client(args)

        call_kwargs = mock_opensearch.call_args[1]
        assert 'prod-cluster.example.com' in call_kwargs['hosts'][0]
        assert call_kwargs['http_auth'] == ('admin', 'supersecret')


class TestDynamicModeGuard:
    """Tests that URL overrides are rejected when dynamic mode is disabled."""

    def setup_method(self):
        self.original_env = {}
        self._env_keys = [
            'OPENSEARCH_URL',
            'OPENSEARCH_USERNAME',
            'OPENSEARCH_PASSWORD',
            'OPENSEARCH_NO_AUTH',
            'AWS_IAM_ARN',
            'AWS_REGION',
            'AWS_PROFILE',
            'AWS_OPENSEARCH_SERVERLESS',
            'OPENSEARCH_HEADER_AUTH',
            'OPENSEARCH_TIMEOUT',
            'OPENSEARCH_SSL_VERIFY',
            'OPENSEARCH_MAX_RESPONSE_SIZE',
            'OPENSEARCH_DYNAMIC_CONNECTION',
        ]
        for key in self._env_keys:
            if key in os.environ:
                self.original_env[key] = os.environ[key]
                del os.environ[key]

        from mcp_server_opensearch.global_state import set_mode

        set_mode('single')

    def teardown_method(self):
        for key in self._env_keys:
            os.environ.pop(key, None)
        for key, value in self.original_env.items():
            os.environ[key] = value

    @patch('opensearch.client.get_aws_region_single_mode')
    @patch('opensearch.client.is_dynamic_mode_enabled', return_value=False)
    def test_url_override_rejected_when_dynamic_disabled(
        self, mock_dynamic, mock_get_region
    ):
        """When dynamic mode is off, opensearch_url override raises ConfigurationError."""
        os.environ['OPENSEARCH_URL'] = 'https://prod-cluster.example.com:9200'
        os.environ['OPENSEARCH_USERNAME'] = 'admin'
        os.environ['OPENSEARCH_PASSWORD'] = 'supersecret'
        mock_get_region.return_value = 'us-east-1'

        args = baseToolArgs(
            opensearch_cluster_name='',
            opensearch_url='https://attacker.evil.com:9200',
        )
        with pytest.raises(ConfigurationError, match='Dynamic connection override is disabled'):
            initialize_client(args)

    @patch('opensearch.client.get_aws_region_single_mode')
    @patch('opensearch.client.is_dynamic_mode_enabled', return_value=False)
    def test_url_override_rejected_even_with_other_overrides(
        self, mock_dynamic, mock_get_region
    ):
        """URL override still raises even when other overrides are provided."""
        os.environ['OPENSEARCH_URL'] = 'https://prod-cluster.example.com:9200'
        os.environ['OPENSEARCH_NO_AUTH'] = 'true'
        mock_get_region.return_value = 'us-east-1'

        args = baseToolArgs(
            opensearch_cluster_name='',
            opensearch_url='https://attacker.evil.com:9200',
            opensearch_timeout=60,
            opensearch_ssl_verify=False,
        )
        with pytest.raises(ConfigurationError, match='Dynamic connection override is disabled'):
            initialize_client(args)


class TestHeaderAuthCredentialIsolation:
    """Tests credential isolation for the header-auth path."""

    def setup_method(self):
        self.original_env = {}
        self._env_keys = [
            'OPENSEARCH_URL',
            'OPENSEARCH_USERNAME',
            'OPENSEARCH_PASSWORD',
            'OPENSEARCH_NO_AUTH',
            'AWS_IAM_ARN',
            'AWS_REGION',
            'AWS_PROFILE',
            'AWS_OPENSEARCH_SERVERLESS',
            'OPENSEARCH_HEADER_AUTH',
            'OPENSEARCH_TIMEOUT',
            'OPENSEARCH_SSL_VERIFY',
            'OPENSEARCH_MAX_RESPONSE_SIZE',
            'OPENSEARCH_DYNAMIC_CONNECTION',
        ]
        for key in self._env_keys:
            if key in os.environ:
                self.original_env[key] = os.environ[key]
                del os.environ[key]

        from mcp_server_opensearch.global_state import set_mode

        set_mode('single')

    def teardown_method(self):
        for key in self._env_keys:
            os.environ.pop(key, None)
        for key, value in self.original_env.items():
            os.environ[key] = value

    @patch('opensearch.client._get_auth_from_headers')
    @patch('opensearch.client._create_opensearch_client')
    @patch('opensearch.client.get_aws_region_single_mode')
    def test_header_url_does_not_inherit_env_creds(
        self, mock_get_region, mock_create_client, mock_get_headers
    ):
        """Header-auth URL must not carry env credentials."""
        os.environ['OPENSEARCH_URL'] = 'https://prod-cluster.example.com:9200'
        os.environ['OPENSEARCH_USERNAME'] = 'admin'
        os.environ['OPENSEARCH_PASSWORD'] = 'supersecret'
        os.environ['OPENSEARCH_HEADER_AUTH'] = 'true'
        mock_get_region.return_value = 'us-east-1'
        mock_create_client.return_value = Mock()

        mock_get_headers.return_value = {
            'opensearch_url': 'https://other-cluster.example.com:9200',
        }

        args = baseToolArgs(opensearch_cluster_name='')
        initialize_client(args)

        call_kwargs = mock_create_client.call_args[1]
        assert call_kwargs['opensearch_url'] == 'https://other-cluster.example.com:9200'
        assert call_kwargs['opensearch_username'] == ''
        assert call_kwargs['opensearch_password'] == ''
        assert call_kwargs['iam_arn'] == ''

    @patch('opensearch.client._get_auth_from_headers')
    @patch('opensearch.client._create_opensearch_client')
    @patch('opensearch.client.get_aws_region_single_mode')
    def test_header_url_with_header_creds_works(
        self, mock_get_region, mock_create_client, mock_get_headers
    ):
        """Header providing both URL and credentials should work."""
        os.environ['OPENSEARCH_URL'] = 'https://prod-cluster.example.com:9200'
        os.environ['OPENSEARCH_USERNAME'] = 'admin'
        os.environ['OPENSEARCH_PASSWORD'] = 'supersecret'
        os.environ['OPENSEARCH_HEADER_AUTH'] = 'true'
        mock_get_region.return_value = 'us-east-1'
        mock_create_client.return_value = Mock()

        mock_get_headers.return_value = {
            'opensearch_url': 'https://other-cluster.example.com:9200',
            'opensearch_username': 'header-user',
            'opensearch_password': 'header-pass',
        }

        args = baseToolArgs(opensearch_cluster_name='')
        initialize_client(args)

        call_kwargs = mock_create_client.call_args[1]
        assert call_kwargs['opensearch_url'] == 'https://other-cluster.example.com:9200'
        assert call_kwargs['opensearch_username'] == 'header-user'
        assert call_kwargs['opensearch_password'] == 'header-pass'

    @patch('opensearch.client._get_auth_from_headers')
    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_single_mode')
    def test_no_header_url_uses_env_normally(
        self, mock_get_region, mock_opensearch, mock_get_headers
    ):
        """When header auth is on but no URL in headers, env config is used normally."""
        os.environ['OPENSEARCH_URL'] = 'https://prod-cluster.example.com:9200'
        os.environ['OPENSEARCH_USERNAME'] = 'admin'
        os.environ['OPENSEARCH_PASSWORD'] = 'supersecret'
        os.environ['OPENSEARCH_HEADER_AUTH'] = 'true'
        mock_get_region.return_value = 'us-east-1'
        mock_opensearch.return_value = Mock()

        mock_get_headers.return_value = {}  # No URL in headers

        args = baseToolArgs(opensearch_cluster_name='')
        initialize_client(args)

        call_kwargs = mock_opensearch.call_args[1]
        assert 'prod-cluster.example.com' in call_kwargs['hosts'][0]
        assert call_kwargs['http_auth'] == ('admin', 'supersecret')


class TestAllowlist:
    """Tests for OPENSEARCH_ALLOWED_URLS allowlist behavior."""

    def setup_method(self):
        self.original_env = {}
        self._env_keys = [
            'OPENSEARCH_URL',
            'OPENSEARCH_USERNAME',
            'OPENSEARCH_PASSWORD',
            'OPENSEARCH_NO_AUTH',
            'AWS_IAM_ARN',
            'AWS_REGION',
            'AWS_PROFILE',
            'AWS_OPENSEARCH_SERVERLESS',
            'OPENSEARCH_HEADER_AUTH',
            'OPENSEARCH_TIMEOUT',
            'OPENSEARCH_SSL_VERIFY',
            'OPENSEARCH_MAX_RESPONSE_SIZE',
            'OPENSEARCH_DYNAMIC_CONNECTION',
            'OPENSEARCH_ALLOWED_URLS',
        ]
        for key in self._env_keys:
            if key in os.environ:
                self.original_env[key] = os.environ[key]
                del os.environ[key]

        from mcp_server_opensearch.global_state import set_mode

        set_mode('single')

    def teardown_method(self):
        for key in self._env_keys:
            os.environ.pop(key, None)
        for key, value in self.original_env.items():
            os.environ[key] = value

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_single_mode')
    @patch('opensearch.client.is_dynamic_mode_enabled', return_value=True)
    def test_allowed_url_inherits_env_credentials(
        self, mock_dynamic, mock_get_region, mock_opensearch
    ):
        """When URL matches allowlist, env credentials are used normally."""
        os.environ['OPENSEARCH_URL'] = 'https://default-cluster.example.com:9200'
        os.environ['OPENSEARCH_USERNAME'] = 'admin'
        os.environ['OPENSEARCH_PASSWORD'] = 'supersecret'
        os.environ['OPENSEARCH_ALLOWED_URLS'] = (
            'https://cluster-a.example.com:9200,https://cluster-b.example.com:9200'
        )
        mock_get_region.return_value = 'us-east-1'
        mock_opensearch.return_value = Mock()

        args = baseToolArgs(
            opensearch_cluster_name='',
            opensearch_url='https://cluster-a.example.com:9200',
        )
        initialize_client(args)

        call_kwargs = mock_opensearch.call_args[1]
        assert 'cluster-a.example.com' in call_kwargs['hosts'][0]
        assert call_kwargs['http_auth'] == ('admin', 'supersecret')

    @patch('opensearch.client.get_aws_region_single_mode')
    @patch('opensearch.client.is_dynamic_mode_enabled', return_value=True)
    def test_disallowed_url_raises_error(self, mock_dynamic, mock_get_region):
        """When URL does NOT match allowlist, ConfigurationError is raised."""
        os.environ['OPENSEARCH_URL'] = 'https://default-cluster.example.com:9200'
        os.environ['OPENSEARCH_USERNAME'] = 'admin'
        os.environ['OPENSEARCH_PASSWORD'] = 'supersecret'
        os.environ['OPENSEARCH_ALLOWED_URLS'] = 'https://cluster-a.example.com:9200'
        mock_get_region.return_value = 'us-east-1'

        args = baseToolArgs(
            opensearch_cluster_name='',
            opensearch_url='https://attacker.evil.com:9200',
        )
        with pytest.raises(ConfigurationError, match='not in the allowed URLs list'):
            initialize_client(args)

    @patch('opensearch.client.AsyncOpenSearch')
    @patch('opensearch.client.get_aws_region_single_mode')
    @patch('opensearch.client.is_dynamic_mode_enabled', return_value=True)
    def test_wildcard_pattern_matches(
        self, mock_dynamic, mock_get_region, mock_opensearch
    ):
        """Wildcard patterns in allowlist should match."""
        os.environ['OPENSEARCH_URL'] = 'https://default.example.com:443'
        os.environ['OPENSEARCH_USERNAME'] = 'admin'
        os.environ['OPENSEARCH_PASSWORD'] = 'secret'
        os.environ['OPENSEARCH_ALLOWED_URLS'] = 'https://*.us-east-1.es.amazonaws.com:443'
        mock_get_region.return_value = 'us-east-1'
        mock_opensearch.return_value = Mock()

        args = baseToolArgs(
            opensearch_cluster_name='',
            opensearch_url='https://my-domain.us-east-1.es.amazonaws.com:443',
        )
        initialize_client(args)

        call_kwargs = mock_opensearch.call_args[1]
        assert 'my-domain.us-east-1.es.amazonaws.com' in call_kwargs['hosts'][0]
        assert call_kwargs['http_auth'] == ('admin', 'secret')

    @patch('opensearch.client.get_aws_region_single_mode')
    @patch('opensearch.client.is_dynamic_mode_enabled', return_value=True)
    def test_wildcard_pattern_wrong_scheme_rejects(self, mock_dynamic, mock_get_region):
        """Scheme must match even with wildcard host."""
        os.environ['OPENSEARCH_URL'] = 'https://default.example.com:443'
        os.environ['OPENSEARCH_ALLOWED_URLS'] = 'https://*.example.com:443'
        mock_get_region.return_value = 'us-east-1'

        args = baseToolArgs(
            opensearch_cluster_name='',
            opensearch_url='http://evil.example.com:443',  # http not https
        )
        with pytest.raises(ConfigurationError, match='not in the allowed URLs list'):
            initialize_client(args)

    @patch('opensearch.client.get_aws_region_single_mode')
    @patch('opensearch.client.is_dynamic_mode_enabled', return_value=True)
    def test_no_allowlist_raises_error(
        self, mock_dynamic, mock_get_region
    ):
        """Without allowlist, dynamic URL raises ConfigurationError."""
        os.environ['OPENSEARCH_URL'] = 'https://prod-cluster.example.com:9200'
        os.environ['OPENSEARCH_USERNAME'] = 'admin'
        os.environ['OPENSEARCH_PASSWORD'] = 'supersecret'
        # No OPENSEARCH_ALLOWED_URLS set
        mock_get_region.return_value = 'us-east-1'

        args = baseToolArgs(
            opensearch_cluster_name='',
            opensearch_url='https://other-cluster.example.com:9200',
            opensearch_no_auth=True,
        )
        with pytest.raises(ConfigurationError, match='OPENSEARCH_ALLOWED_URLS'):
            initialize_client(args)

    @patch('opensearch.client._create_opensearch_client')
    @patch('opensearch.client.get_aws_region_single_mode')
    @patch('opensearch.client.is_dynamic_mode_enabled', return_value=True)
    def test_allowed_url_with_aws_iam_inherits_region(
        self, mock_dynamic, mock_get_region, mock_create_client
    ):
        """Allowed URL inherits AWS region and IAM ARN from env."""
        os.environ['OPENSEARCH_URL'] = 'https://default.us-east-1.es.amazonaws.com:443'
        os.environ['AWS_IAM_ARN'] = 'arn:aws:iam::123456789:role/my-role'
        os.environ['OPENSEARCH_ALLOWED_URLS'] = 'https://*.us-east-1.es.amazonaws.com:443'
        mock_get_region.return_value = 'us-east-1'
        mock_create_client.return_value = Mock()

        args = baseToolArgs(
            opensearch_cluster_name='',
            opensearch_url='https://other-domain.us-east-1.es.amazonaws.com:443',
        )
        initialize_client(args)

        call_kwargs = mock_create_client.call_args[1]
        assert call_kwargs['opensearch_url'] == 'https://other-domain.us-east-1.es.amazonaws.com:443'
        assert call_kwargs['iam_arn'] == 'arn:aws:iam::123456789:role/my-role'
        assert call_kwargs['aws_region'] == 'us-east-1'
