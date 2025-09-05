"""
Action: Network connectivity and API ping.

This action tests network connectivity by pinging configured URLs
or performing HTTP requests to verify API endpoints are reachable.
"""

import time
import requests
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.context import AppContext


def ping(ctx: "AppContext") -> str:
    """
    Test network connectivity and API endpoints.

    Pings configured URLs and reports connectivity status.

    Args:
        ctx: The application's context containing configuration and logging.

    Returns:
        str: Connectivity test results.
    """
    ctx.logger.info("Executing action: network.ping")

    results = []
    base_url = ctx.config.network.api_base_url
    timeout = ctx.config.network.timeout

    ctx.logger.info(f"Testing connectivity to: {base_url}")

    try:
        start_time = time.time()

        # Test basic connectivity
        response = requests.get(base_url, timeout=timeout)

        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds

        if response.status_code == 200:
            results.append(f"✅ {base_url} - OK ({response_time:.1f}ms)")
        else:
            results.append(
                f"⚠️  {base_url} - HTTP {response.status_code} ({response_time:.1f}ms)"
            )
        ctx.logger.info(f"Network ping successful: {response_time:.1f}ms")

    except requests.exceptions.Timeout:
        results.append(f"❌ {base_url} - Timeout ({timeout}s)")
        ctx.logger.warning(f"Timeout connecting to {base_url}")

    except requests.exceptions.ConnectionError:
        results.append(f"❌ {base_url} - Connection failed")
        ctx.logger.warning(f"Connection failed to {base_url}")

    except Exception as e:
        results.append(f"❌ {base_url} - Error: {str(e)}")
        ctx.logger.error(f"Network test failed: {e}")

    return "\n".join(results)


def test_connectivity(ctx: "AppContext") -> str:
    """
    Test basic internet connectivity.

    Args:
        ctx: The application's context containing configuration and logging.

    Returns:
        str: Connectivity status.
    """
    ctx.logger.info("Testing basic internet connectivity")

    import requests

    test_urls = [
        "https://www.google.com",
        "https://www.github.com",
        "https://httpbin.org",
    ]

    success_count = 0

    for url in test_urls:
        try:
            response = requests.head(url, timeout=5)
            if response.status_code < 400:
                success_count += 1
                ctx.logger.debug(f"✓ {url} - OK")
            else:
                ctx.logger.debug(f"✗ {url} - HTTP {response.status_code}")
        except Exception as e:
            ctx.logger.debug(f"✗ {url} - {str(e)}")

    if success_count > 0:
        result = f"✓ Internet connectivity: {success_count}/{len(test_urls)} endpoints reachable"
        ctx.logger.info(result)
        return result
    else:
        result = "❌ No internet connectivity detected"
        ctx.logger.warning(result)
        return result
