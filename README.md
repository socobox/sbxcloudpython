# SbxCloudPython

A Python client library for interacting with SbxCloud services.

## Overview

SbxCloudPython is a Python client library that provides a convenient way to interact with SbxCloud services. It supports both synchronous and asynchronous operations, making it flexible for various use cases.

## Requirements

- Python 3.5 or higher
- Dependencies:
  - `asyncio` - For asynchronous operations
  - `aiohttp` - For HTTP requests

## Installation

You can install the library using pip:

```bash
pip install sbxpy
```

## Features

- Query building with type hints for better IDE support
- Asynchronous operations with asyncio
- Callback-based API for synchronous code
- Support for complex queries with reference joins
- Pagination handling

## Basic Usage

### Initialization

```python
from sbxpy import SbxCore

# Initialize the SbxCore instance
sbx = SbxCore()
sbx.initialize(domain="your_domain", app_key="your_app_key", base_url="https://api.sbxcloud.com")

# For async operations
import asyncio

async def main():
    # Login to SbxCloud
    login_result = await sbx.login("your_email", "your_password", "your_domain")
    print(login_result)

# Run the async function
asyncio.run(main())
```

### Building Queries

```python
# Create a query to find data
find = sbx.with_model("your_model")
find.and_where_is_equal("field_name", "value")
find.and_where_greater_than("numeric_field", 100)
find.set_page(1)
find.set_page_size(50)

# Execute the query asynchronously
async def execute_query():
    results = await find.find()
    print(results)

asyncio.run(execute_query())
```

### Using Callbacks

```python
# Initialize with event loop management
sbx = SbxCore(manage_loop=True)
sbx.initialize(domain="your_domain", app_key="your_app_key", base_url="https://api.sbxcloud.com")

# Define a callback function
def on_login_complete(error, data):
    if error:
        print(f"Error: {error}")
    else:
        print(f"Login successful: {data}")

# Use the callback API
sbx.loginCallback("your_email", "your_password", "your_domain", on_login_complete)

# Don't forget to close the connection when done
sbx.close_connection()
```

## Advanced Usage

### Reference Joins

```python
# Create a query with reference joins
find = sbx.with_model("your_model")
reference_join = find.and_where_reference_join_between("field_in_model", "field_in_referenced_model")
filter_join = reference_join.in_model("referenced_model")
filter_join.filter_where_is_equal("value")

# Execute the query
async def execute_complex_query():
    results = await find.find()
    print(results)

asyncio.run(execute_complex_query())
```

### Fetching Related Models

```python
find = sbx.with_model("your_model")
find.fetch_models(["related_model1", "related_model2"])
find.and_where_is_equal("field_name", "value")

async def fetch_with_related():
    results = await find.find()
    print(results)

asyncio.run(fetch_with_related())
```

## Testing

You can test the library using the provided `test.py` file. Before executing it, make sure to configure your credentials in the environment.

## License

This project is licensed under the terms of the license included in the repository.

