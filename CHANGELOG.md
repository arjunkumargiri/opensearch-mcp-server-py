# CHANGELOG

Inspired from [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [Unreleased]

### Added
- Add `GenericOpenSearchApiTool` - A flexible, general-purpose tool that can interact with any OpenSearch API endpoint, addressing tool explosion and reducing context size. Supports all HTTP methods with write operation protection via `OPENSEARCH_SETTINGS_ALLOW_WRITE` environment variable. Closes [#109](https://github.com/opensearch-project/opensearch-mcp-server-py/issues/109)
- Add new operational tools for comprehensive OpenSearch cluster analysis: `GetClusterStateTool`, `GetSegmentsTool`, `CatNodesTool`, `GetNodesTool`, `GetIndexInfoTool`, `GetIndexStatsTool`, `GetQueryInsightsTool`, `GetNodesHotThreadsTool`, `GetAllocationTool`, and `GetLongRunningTasksTool` and test cases ([#78](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/78))
- Add include_detail as optional parameter to ListIndexTool ([#97](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/97))
- Allow customizing tool argument descriptions via configuration ([#100](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/100))
- Enhance tool filtering ([#101](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/101))
- Add core tools as a category ([#103](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/103))
- set stateless=True for streaming server by default ([#104](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/104))

### Fixed

### Removed

## [Released 0.3.2]

- Add timeout as optional parameter ([#92](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/92))

## [Released 0.3.1]

### Added
- Add stateless HTTP as an optional parameter to `streaming_server` ([#86](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/86))

## [Released 0.3]

### Added
- Allow overriding tool properties via configuration ([#69](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/69))
- Extend list indices tool ([#68](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/68))
- Add `OPENSEARCH_NO_AUTH` environment variable for connecting to clusters without authentication

### Fixed
- Handle Tool Filtering failure gracefully and define priority to the AWS Region definitions ([#74](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/74))
- Fix Tool Renaming Edge cases ([#80](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/80))

## [Released 0.2.2]
### Fixed
- Fix endpoint selection bug in ClusterHealthTool and CountTool ([#59](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/59))
- Fix Serverless issues ([#61](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/61))

## [Released 0.2]
### Added
- Add OpenSearch URl as an optional parameter for tool calls ([#20](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/20))
- Add CI to run unit tests ([#22](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/22))
- Add support for AWS OpenSearch serverless ([#31](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/31))
- Add filtering tools based on OpenSearch version compatibility defined in TOOL_REGISTRY ([#32](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/32))
- Add `ClusterHealthTool`, `CountTool`,  `MsearchTool`, and `ExplainTool` through OpenSearch API specification ([#33](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/33))
- Add support for Multiple OpenSearch cluster Connectivity ([#45](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/45))
- Add tool filter feature [#46](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/46)
- Support Streamable HTTP Protocol [#47](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/47)
- Add `OPENSEARCH_SSL_VERIFY` environment variable ([#40](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/40))
### Removed

### Fixed
- Fix AWS auth requiring `AWS_REGION` environment variable to be set, will now support using region set via `~/.aws/config` ([#28](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/28))
- Fix OpenSearch client to use refreshable credentials ([#13](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/13))
- fix publish release ci and bump version on main ([#49](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/49))
- fix OpenAPI tools schema, handle NDJSON ([#52](https://github.com/opensearch-project/opensearch-mcp-server-py/pull/52))
### Security
