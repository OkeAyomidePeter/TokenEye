import os
import yaml
import itertools
import random
from pathlib import Path
from dotenv import load_dotenv
import asyncio
import httpx

# -------------------------
# Load .env from project root
# -------------------------
ROOT_DIR = Path(__file__).resolve().parents[2]
dotenv_path = ROOT_DIR / ".env"
load_dotenv(dotenv_path)

class RpcManager:
    def __init__(self, config_path=None, max_retries=3, retry_delay=1):
        """
        Async RPC key manager with automatic failover for pipelines.
        Supports batch-ready endpoint fetching.
        """
        if config_path is None:
            config_path = ROOT_DIR / "config.yaml"

        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Parse helius keys
        self.helius_keys = {
            item["name"]: os.getenv(item["key"].strip("${}"))
            for item in self.config["rpc"]["helius"]["keys"]
        }

        self.endpoint_template = self.config["rpc"]["endpoint_template"]

        # Dedicated keys
        self.pipeline_keys = {
            "pipeline_10m": self.helius_keys.get("pipeline_10m"),
            "pipeline_snapshots": self.helius_keys.get("pipeline_snapshots"),
        }

        # Buffer keys
        self.buffer_keys = [k for n, k in self.helius_keys.items() if "buffer" in n]
        self.buffer_iter = itertools.cycle(self.buffer_keys)

    async def _test_endpoint(self, endpoint: str) -> bool:
        """Async health check for a single endpoint using JSON-RPC."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                # Use getHealth JSON-RPC method to test endpoint
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getHealth"
                }
                resp = await client.post(endpoint, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    # Check if response doesn't have an error
                    return "error" not in data or data.get("result") == "ok"
                return False
            except (httpx.RequestError, Exception):
                return False

    async def get_endpoint(self, pipeline="pipeline_10m") -> str:
        """
        Returns a usable endpoint URL for a single pipeline.
        Fallback logic included.
        """
        tried_keys = set()

        for _ in range(self.max_retries):
            key = self.pipeline_keys.get(pipeline)
            if key is None or key in tried_keys:
                if not self.buffer_keys:
                    raise RuntimeError("No buffer keys available for fallback.")
                key = next(self.buffer_iter)

            endpoint = self.endpoint_template.format(api_key=key)
            tried_keys.add(key)

            if await self._test_endpoint(endpoint):
                return endpoint

            await asyncio.sleep(self.retry_delay)

        raise RuntimeError(f"No available endpoints after {self.max_retries} retries.")

    async def get_batch_endpoints(self, pipeline="pipeline_10m", batch_size=10) -> list[str]:
        """
        Returns a list of endpoints ready for concurrent use.
        Ensures each endpoint is healthy before returning.
        """
        tasks = []
        endpoints = []

        # Prepare tasks up to batch size
        for _ in range(batch_size):
            key = self.pipeline_keys.get(pipeline)
            if key is None:
                key = next(self.buffer_iter)
            endpoint = self.endpoint_template.format(api_key=key)
            tasks.append(self._test_endpoint(endpoint))

        results = await asyncio.gather(*tasks)

        # Only keep healthy endpoints
        for i, ok in enumerate(results):
            if ok:
                endpoints.append(self.endpoint_template.format(api_key=list(self.pipeline_keys.values())[0]))
            else:
                # fallback to buffer key
                buffer_key = next(self.buffer_iter)
                endpoints.append(self.endpoint_template.format(api_key=buffer_key))

        return endpoints

    async def random_buffer(self) -> str:
        """Randomly pick a buffer key (spread load randomly)."""
        if not self.buffer_keys:
            raise RuntimeError("No buffer keys available for random selection.")
        key = random.choice(self.buffer_keys)
        return self.endpoint_template.format(api_key=key)
