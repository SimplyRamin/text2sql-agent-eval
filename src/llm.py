# =================================================================================================
#                                           Written by Ramin F.
#                                           Senior AI Engineer
#                            Ferdos.ramin@gmail.com | simplyramin.github.io
# =================================================================================================
import os
import time

import litellm
from dotenv import load_dotenv

from src.budget import budget
from src.cache import get as cache_get
from src.cache import set as cache_set

load_dotenv()

# $ per 1,000,000 tokens - (price_in, price_out). Only hosted models need
# pricing; local Ollama calls are free and never touch this dict.
PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
}


def complete(
    prompt: str,
    model: str,
    provider: str = "local",
    temperature: float = 0.0,
) -> dict:
    use_cache = temperature == 0.0

    if use_cache:
        cached = cache_get(model, temperature, prompt)
        if cached is not None:
            return {**cached, "cached": True, "cost": 0.0}

    if provider == "local":
        if not os.getenv("OLLAMA_HOST"):
            raise RuntimeError(
                "OLLAMA_HOST not set - local inference unavailable on this machine"
            )

        start_time = time.perf_counter()
        response = litellm.completion(
            model=f"ollama/{model}",
            api_base=os.getenv("OLLAMA_HOST"),
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        latency_ms = (time.perf_counter() - start_time) * 1000

        assert isinstance(response, litellm.ModelResponse)
        usage_info = response.usage # type: ignore[attr-defined]
        assert usage_info is not None

        text = response.choices[0].message.content
        usage = {
            "in_tokens": usage_info.prompt_tokens,
            "out_tokens": usage_info.completion_tokens,
        }

        result = {"text": text, "usage": usage, "cost": 0.0, "latency_ms": latency_ms}
        if use_cache:
            cache_set(model, temperature, prompt, result)
        return {**result, "cached": False}


    if provider == "hosted":
        if not os.getenv("API_BASE_URL") or not os.getenv("API_KEY"):
            raise RuntimeError(
                "API_BASE_URL / API_KEY not set - hosted inference unavailable"
            )
        if model not in PRICING:
            raise RuntimeError(f"No pricing entry for hosted model '{model}' - add it to PRICING")

        start_time = time.perf_counter()
        response = litellm.completion(
            model=f"openai/{model}",
            api_base=os.getenv("API_BASE_URL"),
            api_key=os.getenv("API_KEY"),
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
            num_retries=2,
        )
        latency_ms = (time.perf_counter() - start_time) * 1000

        assert isinstance(response, litellm.ModelResponse)
        usage_info = response.usage # type: ignore[attr-defined]
        assert usage_info is not None

        text = response.choices[0].message.content
        in_tokens = usage_info.prompt_tokens
        out_tokens = usage_info.completion_tokens

        price_in, price_out = PRICING[model]
        cost = budget.charge(in_tokens, out_tokens, price_in, price_out)

        result = {
            "text": text,
            "usage": {"in_tokens": in_tokens, "out_tokens": out_tokens},
            "cost": cost,
            "latency_ms": latency_ms,
        }
        if use_cache:
            cache_set(model, temperature, prompt, result)
        return {**result, "cached": False}

    raise ValueError(f"Unknown provider: {provider!r}")
