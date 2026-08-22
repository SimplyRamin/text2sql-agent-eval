# =================================================================================================
#                                           Written by Ramin F.
#                                           Senior AI Engineer
#                            Ferdos.ramin@gmail.com | simplyramin.github.io
# =================================================================================================
import os

from dotenv import load_dotenv

load_dotenv()


class BudgetExceededError(RuntimeError):
    pass


class Budget:
    def __init__(self, limit_usd: float | None = None):
        if limit_usd is None:
            limit_usd = float(os.getenv("BUDGET_LIMIT_USD", "3.00"))
        self.limit = limit_usd
        self.spent = 0.0

    def charge(self, in_tokens: int, out_tokens: int, price_in: float, price_out: float) -> float:
        """
        Raises BEFORE recording if this call would exceed the limit. Note: for a 
        real hosted API call, in_tokens/out_tokens are the actual usage from a 
        call that has already happened - this stops the NEXT call in a loop,
        not the one that crosses the ceiling. With a $3 ceiling and bounded
        per-call max_tokens, worst-case overshoot is one call's cost (pennies).
        True pre-call prevention needs a token-estimate gate (the --dry-run 
        flag from PROJECT_BRIEF §6), which is out of scope here.
        """
        cost = (in_tokens / 1e6) * price_in + (out_tokens / 1e6) * price_out
        if self.spent + cost > self.limit:
            raise BudgetExceededError(
                f"Budget exhausted: spent=${self.spent:.4f}, "
                f"limit=${self.limit:.2f}, this call would cost ${cost:.4f}"
            )
        self.spent += cost
        return cost


budget = Budget()