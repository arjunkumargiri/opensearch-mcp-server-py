import pytest
from semver import Version
from unittest.mock import patch, MagicMock
from tools.utils import is_tool_compatible
from tools.tool_filter import get_tools, process_tool_filter
from tools.tool_params import baseToolArgs
import copy

# A dictionary for mocking TOOL_REGISTRY
MOCK_TOOL_REGISTRY = {
    'ListIndexTool': {
        'display_name': 'ListIndexTool',
        'description': 'List indices',
        'input_schema': {'type': 'object', 'properties': {'param1': {'type': 'string'}}},
        'function': MagicMock(),
        'args_model': MagicMock(),
        'min_version': '1.0.0',
        'max_version': '3.0.0',
    },
    'SearchIndexTool': {
        'display_name': 'SearchIndexTool',
        'description': 'Search an index',
        'input_schema': {
            'type': 'object',
            'properties': {
                'opensearch_cluster_name': {'type': 'string'},
                'query': {'type': 'object'},
            },
        },
        'function': MagicMock(),
        'args_model': MagicMock(),
        'min_version': '2.0.0',
        'max_version': '3.0.0',
    },
}


class TestIsToolCompatible:
    def test_version_within_range(self):
        tool_info = {'min_version': '1.0.0', 'max_version': '3.0.0'}
        assert is_tool_compatible(Version.parse('2.0.0'), tool_info) is True

    def test_version_below_min(self):
        tool_info = {'min_version': '2.0.0', 'max_version': '3.0.0'}
        assert is_tool_compatible(Version.parse('1.5.0'), tool_info) is False

    def test_version_above_max(self):
        tool_info = {'min_version': '1.0.0', 'max_version': '2.0.0'}
        assert is_tool_compatible(Version.parse('2.1.0'), tool_info) is False

    def test_version_equal_to_min(self):
        tool_info = {'min_version': '1.0.0', 'max_version': '3.0.0'}
        assert is_tool_compatible(Version.parse('1.0.0'), tool_info) is True

    def test_version_equal_to_max(self):
        tool_info = {'min_version': '1.0.0', 'max_version': '3.0.0'}
        assert is_tool_compatible(Version.parse('3.0.0'), tool_info) is True

    def test_version_only_patch_not_provided(self):
        tool_info = {'min_version': '2.5', 'max_version': '3'}
        assert is_tool_compatible(Version.parse('2.5.1'), tool_info) is True
        assert is_tool_compatible(Version.parse('2.15.0'), tool_info) is True
        assert is_tool_compatible(Version.parse('3.0.0'), tool_info) is True

    def test_default_tool_info(self):
        # Should be True for almost any reasonable version
        assert is_tool_compatible(Version.parse('1.2.3')) is True
        assert is_tool_compatible(Version.parse('99.0.0')) is True
        assert is_tool_compatible(Version.parse('0.0.1')) is True

    def test_invalid_version_strings(self):
        # If min_version or max_version is not a valid semver, should raise ValueError
        with pytest.raises(ValueError):
            is_tool_compatible(Version.parse('1.0.0'), {'min_version': 'not_a_version'})
        with pytest.raises(ValueError):
            is_tool_compatible(Version.parse('1.0.0'), {'max_version': 'not_a_version'})


class TestGetTools:
    """Test cases for the get_tools function."""

    @pytest.fixture
    def mock_tool_registry(self):
        """Return a deep copy of the mock tool registry for isolation."""
        return copy.deepcopy(MOCK_TOOL_REGISTRY)

    @pytest.fixture
    def mock_patches(self):
        """Set up common patches for get_tools tests."""
        with (
            patch('tools.tool_filter.get_opensearch_version') as mock_get_version,
            patch('tools.tool_filter.is_tool_compatible') as mock_is_compatible,
        ):
            yield mock_get_version, mock_is_compatible

    def test_get_tools_multi_mode_returns_all_tools(self, mock_tool_registry):
        """Test that multi mode returns all tools with base fields intact."""
        result = get_tools(mock_tool_registry, mode='multi')
        assert result == mock_tool_registry
        assert 'param1' in result['ListIndexTool']['input_schema']['properties']
        assert 'opensearch_cluster_name' in result['SearchIndexTool']['input_schema']['properties']

    def test_get_tools_single_mode_filters_and_removes_base_fields(
        self, mock_tool_registry, mock_patches
    ):
        """Test that single mode filters by version AND removes base fields."""
        mock_get_version, mock_is_compatible = mock_patches

        # Setup mocks
        mock_get_version.return_value = Version.parse('2.5.0')

        # Mock compatibility: only ListIndexTool should be compatible
        mock_is_compatible.side_effect = (
            lambda version, tool_info: tool_info['min_version'] == '1.0.0'
        )

        # Patch TOOL_REGISTRY to use our mock registry
        with patch('tools.tool_filter.TOOL_REGISTRY', mock_tool_registry):
            # Call get_tools in single mode
            result = get_tools(mock_tool_registry, mode='single')

            # Assertions
            assert 'ListIndexTool' in result
            assert 'SearchIndexTool' not in result
            assert 'param1' in result['ListIndexTool']['input_schema']['properties']
            assert (
                'opensearch_cluster_name'
                not in result['ListIndexTool']['input_schema']['properties']
            )

    @patch.dict('os.environ', {'AWS_OPENSEARCH_SERVERLESS': 'true'})
    def test_get_tools_single_mode_serverless_passes_compatibility_check(
        self, mock_tool_registry, mock_patches
    ):
        """Test that serverless mode passes version compatibility checks."""
        mock_get_version, mock_is_compatible = mock_patches

        # Setup mocks
        mock_get_version.return_value = None
        mock_is_compatible.return_value = True  # Should return True for serverless mode

        # Patch TOOL_REGISTRY to use our mock registry
        with patch('tools.tool_filter.TOOL_REGISTRY', mock_tool_registry):
            # Call get_tools in single mode with serverless environment
            result = get_tools(mock_tool_registry, mode='single')

            # is_tool_compatible should be called with None version, and should return True for serverless
            mock_is_compatible.assert_called()
            # Verify all calls were made with None as the version
            for call in mock_is_compatible.call_args_list:
                if len(call.args) > 0:  # Check if there are positional arguments
                    assert call.args[0] is None, f'Expected None version, got {call.args[0]}'

            # Both tools should be enabled in serverless mode
            assert 'ListIndexTool' in result
            assert 'SearchIndexTool' in result

    def test_get_tools_single_mode_handles_missing_properties(self, mock_patches):
        """Test that single mode handles schemas without properties field."""
        mock_get_version, mock_is_compatible = mock_patches

        # Create tool with missing properties
        tool_without_properties = {
            'ListIndexTool': {
                'display_name': 'ListIndexTool',
                'description': 'List indices',
                'input_schema': {'type': 'object', 'title': 'ListIndexArgs'},
                'function': MagicMock(),
                'args_model': MagicMock(),
                'min_version': '1.0.0',
                'max_version': '3.0.0',
            }
        }
        mock_get_version.return_value = Version.parse('2.5.0')
        mock_is_compatible.return_value = True

        # Patch TOOL_REGISTRY to use our test tool registry
        with patch('tools.tool_filter.TOOL_REGISTRY', tool_without_properties):
            # Call get_tools in single mode - should not raise error
            result = get_tools(tool_without_properties, mode='single')
            assert 'ListIndexTool' in result
            assert 'properties' not in result['ListIndexTool']['input_schema']

    def test_get_tools_default_mode_is_single(self, mock_tool_registry, mock_patches):
        """Test that get_tools defaults to single mode."""
        mock_get_version, mock_is_compatible = mock_patches

        mock_get_version.return_value = Version.parse('2.5.0')
        mock_is_compatible.return_value = True

        # Patch TOOL_REGISTRY to use our mock registry
        with patch('tools.tool_filter.TOOL_REGISTRY', mock_tool_registry):
            # Call get_tools without specifying mode
            result = get_tools(mock_tool_registry)
            assert (
                'opensearch_cluster_name'
                not in result['SearchIndexTool']['input_schema']['properties']
            )

    def test_get_tools_logs_version_info(self, mock_tool_registry, mock_patches, caplog):
        """Test that get_tools logs version information in single mode."""
        mock_get_version, mock_is_compatible = mock_patches
        mock_get_version.return_value = Version.parse('2.5.0')
        mock_is_compatible.return_value = True

        # Patch TOOL_REGISTRY to use our mock registry
        with patch('tools.tool_filter.TOOL_REGISTRY', mock_tool_registry):
            # Call get_tools in single mode with logging capture
            with caplog.at_level('INFO'):
                get_tools(mock_tool_registry, mode='single')
                assert 'Connected OpenSearch version: 2.5.0' in caplog.text


class TestProcessToolFilter:
    """Test cases for the process_tool_filter function."""

    def setup_method(self):
        """Set up a fresh copy of the tool registry for each test."""
        self.tool_registry = {
            'ListIndexTool': {'display_name': 'ListIndexTool', 'http_methods': 'GET'},
            'SearchIndexTool': {'display_name': 'SearchIndexTool', 'http_methods': 'GET, POST'},
            'MsearchTool': {'display_name': 'MsearchTool', 'http_methods': 'GET, POST'},
            'ExplainTool': {'display_name': 'ExplainTool', 'http_methods': 'GET, POST'},
            'ClusterHealthTool': {'display_name': 'ClusterHealthTool', 'http_methods': 'GET'},
            'IndicesCreateTool': {'display_name': 'IndicesCreateTool', 'http_methods': 'PUT'},
            'IndicesStatsTool': {'display_name': 'IndicesStatsTool', 'http_methods': 'GET'},
            'CountTool': {'display_name': 'CustomCountTool', 'http_methods': 'GET'},
            'ListModelTool': {'display_name': 'ModelListTool', 'http_methods': 'GET'},
        }
        self.category_to_tools = {
            'critical': ['SearchIndexTool', 'ExplainTool'],
            'admin': ['ClusterHealthTool', 'IndicesStatsTool'],
        }

    def test_process_tool_filter_config(self):
        """Test processing tool filter from a YAML config file."""
        process_tool_filter(
            tool_registry=self.tool_registry,
            filter_path='tests/tools/test_config.yml',
            tool_categories=self.category_to_tools,
        )

        # Core tools, enabled by default
        assert 'ClusterHealthTool' in self.tool_registry
        assert 'ListIndexTool' in self.tool_registry

        # Non-core tools, but enabled in test_config.yml
        assert 'IndicesStatsTool' in self.tool_registry

        # Core tools, but disabled in test_config.yml
        assert 'MsearchTool' not in self.tool_registry

        # Tools are in the 'critical' category which is disabled in test_config.yml
        assert 'SearchIndexTool' not in self.tool_registry
        assert 'ExplainTool' not in self.tool_registry

    def test_process_tool_filter_env(self):
        """Test processing tool filter from environment variables."""
        # Call the function with environment variables
        process_tool_filter(
            tool_registry=self.tool_registry,
            disabled_tools='ExplainTool',
            disabled_tools_regex='search.*',
            allow_write=True,
        )

        # Core tools, enabled by default
        assert 'ListIndexTool' in self.tool_registry
        assert 'ClusterHealthTool' in self.tool_registry
        assert 'MsearchTool' in self.tool_registry

        # Non-core tools, disabled by default
        assert 'IndicesCreateTool' not in self.tool_registry
        assert 'IndicesStatsTool' not in self.tool_registry

        # In disabled_tools_regex and disabled_tools
        assert 'SearchIndexTool' not in self.tool_registry
        assert 'ExplainTool' not in self.tool_registry

    def test_process_tool_filter_rename_tool(self):
        """Test processing tool filtering with tool renaming feature"""
        process_tool_filter(
            tool_registry=self.tool_registry,
            enabled_tools='ModelListTool',
            disabled_tools='CountTool',
            disabled_tools_regex='list.*',
            allow_write=True,
        )
        assert 'CountTool' in self.tool_registry  # Renamed to CustomCountTool
        assert 'ListModelTool' in self.tool_registry  # Renamed to ModelListTool

        process_tool_filter(
            tool_registry=self.tool_registry,
            disabled_tools='CustomCountTool',
            disabled_tools_regex='model.*',
            allow_write=True,
        )
        assert 'CustomCountTool' not in self.tool_registry
        assert 'ModelListTool' not in self.tool_registry

    def test_core_tools_default(self):
        """Test core tools enabled by default"""
        process_tool_filter(
            tool_registry=self.tool_registry,
            allow_write=True,
        )

        # Core tools
        assert 'ListIndexTool' in self.tool_registry
        assert 'ClusterHealthTool' in self.tool_registry

        # Non-core tools
        assert 'IndicesStatsTool' not in self.tool_registry
        assert 'ListModelTool' not in self.tool_registry

    def test_disable_core_tools(self):
        """Test disable core tools categories, which is enabled by default"""
        process_tool_filter(
            tool_registry=self.tool_registry,
            disabled_categories='core_tools',
            allow_write=True,
        )

        # Core tools, should be disabled
        assert 'ListIndexTool' not in self.tool_registry
        assert 'ClusterHealthTool' not in self.tool_registry
        assert 'ExplainTool' not in self.tool_registry


class TestAllowWriteSettings:
    """Test cases for the allow_write setting functionality."""

    def setup_method(self):
        """Set up test environment before each test."""
        # Reset the global setting before each test
        from tools.tool_filter import set_allow_write_setting
        set_allow_write_setting(None)
        
        # Save original environment variable
        import os
        self.original_env = os.environ.get('OPENSEARCH_SETTINGS_ALLOW_WRITE')

    def teardown_method(self):
        """Clean up test environment after each test."""
        # Reset the global setting after each test
        from tools.tool_filter import set_allow_write_setting
        set_allow_write_setting(None)
        
        # Restore original environment variable
        import os
        if self.original_env is not None:
            os.environ['OPENSEARCH_SETTINGS_ALLOW_WRITE'] = self.original_env
        elif 'OPENSEARCH_SETTINGS_ALLOW_WRITE' in os.environ:
            del os.environ['OPENSEARCH_SETTINGS_ALLOW_WRITE']

    def test_set_and_get_allow_write_setting(self):
        """Test basic set and get functionality for allow_write setting."""
        from tools.tool_filter import set_allow_write_setting, get_allow_write_setting
        
        # Test setting to False
        set_allow_write_setting(False)
        assert get_allow_write_setting() is False
        
        # Test setting to True
        set_allow_write_setting(True)
        assert get_allow_write_setting() is True

    def test_get_allow_write_setting_fallback_to_env(self):
        """Test that get_allow_write_setting falls back to environment variable when global setting is not set."""
        import os
        from tools.tool_filter import get_allow_write_setting
        
        # Test fallback to env var when set to 'true'
        os.environ['OPENSEARCH_SETTINGS_ALLOW_WRITE'] = 'true'
        assert get_allow_write_setting() is True
        
        # Test fallback to env var when set to 'false'
        os.environ['OPENSEARCH_SETTINGS_ALLOW_WRITE'] = 'false'
        assert get_allow_write_setting() is False
        
        # Test fallback to default (true) when env var not set
        if 'OPENSEARCH_SETTINGS_ALLOW_WRITE' in os.environ:
            del os.environ['OPENSEARCH_SETTINGS_ALLOW_WRITE']
        assert get_allow_write_setting() is True

    @patch('tools.tool_filter.load_yaml_config')
    def test_resolve_allow_write_setting_from_env_only(self, mock_load_yaml):
        """Test _resolve_allow_write_setting with environment variable only."""
        import os
        from tools.tool_filter import _resolve_allow_write_setting
        
        # Test with env var set to true
        os.environ['OPENSEARCH_SETTINGS_ALLOW_WRITE'] = 'true'
        result = _resolve_allow_write_setting()
        assert result is True
        mock_load_yaml.assert_not_called()
        
        # Test with env var set to false
        os.environ['OPENSEARCH_SETTINGS_ALLOW_WRITE'] = 'false'
        result = _resolve_allow_write_setting()
        assert result is False
        mock_load_yaml.assert_not_called()

    @patch('tools.tool_filter.load_yaml_config')
    @patch('os.path.exists')
    def test_resolve_allow_write_setting_from_config_file(self, mock_exists, mock_load_yaml):
        """Test _resolve_allow_write_setting with config file."""
        import os
        from tools.tool_filter import _resolve_allow_write_setting
        
        # Set up mocks
        mock_exists.return_value = True
        mock_config = {
            'tool_filters': {
                'settings': {
                    'allow_write': False
                }
            }
        }
        mock_load_yaml.return_value = mock_config
        
        # Set env var to true, but config should override
        os.environ['OPENSEARCH_SETTINGS_ALLOW_WRITE'] = 'true'
        result = _resolve_allow_write_setting('/path/to/config.yml')
        
        assert result is False  # Config file should override env var
        mock_exists.assert_called_once_with('/path/to/config.yml')
        mock_load_yaml.assert_called_once_with('/path/to/config.yml')

    @patch('tools.tool_filter.load_yaml_config')
    @patch('os.path.exists')
    def test_resolve_allow_write_setting_config_file_not_found(self, mock_exists, mock_load_yaml):
        """Test _resolve_allow_write_setting when config file doesn't exist."""
        import os
        from tools.tool_filter import _resolve_allow_write_setting
        
        # Set up mocks
        mock_exists.return_value = False
        
        # Set env var to false
        os.environ['OPENSEARCH_SETTINGS_ALLOW_WRITE'] = 'false'
        result = _resolve_allow_write_setting('/path/to/nonexistent.yml')
        
        assert result is False  # Should use env var
        mock_exists.assert_called_once_with('/path/to/nonexistent.yml')
        mock_load_yaml.assert_not_called()

    @patch('tools.tool_filter.load_yaml_config')
    @patch('os.path.exists')
    def test_resolve_allow_write_setting_config_file_no_settings(self, mock_exists, mock_load_yaml):
        """Test _resolve_allow_write_setting when config file has no allow_write setting."""
        import os
        from tools.tool_filter import _resolve_allow_write_setting
        
        # Set up mocks
        mock_exists.return_value = True
        mock_config = {
            'tool_filters': {
                'enabled_tools': ['SomeTool']
                # No 'settings' section
            }
        }
        mock_load_yaml.return_value = mock_config
        
        # Set env var to false
        os.environ['OPENSEARCH_SETTINGS_ALLOW_WRITE'] = 'false'
        result = _resolve_allow_write_setting('/path/to/config.yml')
        
        assert result is False  # Should use env var since config has no allow_write
        mock_exists.assert_called_once_with('/path/to/config.yml')
        mock_load_yaml.assert_called_once_with('/path/to/config.yml')

    @patch('tools.tool_filter.load_yaml_config')
    @patch('os.path.exists')
    def test_resolve_allow_write_setting_config_file_error(self, mock_exists, mock_load_yaml):
        """Test _resolve_allow_write_setting when config file loading fails."""
        import os
        from tools.tool_filter import _resolve_allow_write_setting
        
        # Set up mocks
        mock_exists.return_value = True
        mock_load_yaml.side_effect = Exception("YAML parsing error")
        
        # Set env var to true
        os.environ['OPENSEARCH_SETTINGS_ALLOW_WRITE'] = 'true'
        result = _resolve_allow_write_setting('/path/to/config.yml')
        
        assert result is True  # Should fall back to env var on error
        mock_exists.assert_called_once_with('/path/to/config.yml')
        mock_load_yaml.assert_called_once_with('/path/to/config.yml')

    @patch('tools.tool_filter._resolve_allow_write_setting')
    @patch('tools.tool_filter.set_allow_write_setting')
    def test_get_tools_calls_resolve_and_set_allow_write(self, mock_set, mock_resolve):
        """Test that get_tools calls _resolve_allow_write_setting and set_allow_write_setting."""
        from tools.tool_filter import get_tools
        
        # Set up mocks
        mock_resolve.return_value = False
        mock_tool_registry = {
            'TestTool': {
                'display_name': 'TestTool',
                'description': 'Test tool',
                'input_schema': {'type': 'object'},
                'function': MagicMock(),
                'args_model': MagicMock(),
            }
        }
        
        # Test single mode
        with patch('tools.tool_filter.get_opensearch_version'), \
             patch('tools.tool_filter.process_tool_filter'), \
             patch('tools.tool_filter.is_tool_compatible', return_value=True):
            
            get_tools(mock_tool_registry, mode='single', config_file_path='/path/to/config.yml')
            
            mock_resolve.assert_called_once_with('/path/to/config.yml')
            mock_set.assert_called_once_with(False)

