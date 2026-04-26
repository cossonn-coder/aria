# tests/kernel_sandbox.py

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import asyncio
from core.kernel import AriaKernel


TEST_CASES = [
    "explique docker",
    "planifie un système de mémoire",
    "résume mes idées sur ARIA",
]

async def run():
    kernel = AriaKernel()
    print("\n=== ARIA KERNEL SANDBOX ===")
    print("(tape 'exit' ou 'quit' pour quitter proprement)\n")

    while True:
        try:
            msg = input("\nNico > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nAu revoir.")
            break

        if msg in ["exit", "quit", "q"]:
            print("Au revoir.")
            break

        if not msg:
            continue

        result = await kernel.handle_message(
            message=msg,
            metadata={"source": "sandbox"}
        )

        print(f"\nARIA >\n{result}")
        print("\n-------------------------")

        # =====================================================
        # COGNITIVE TRACE OUTPUT (NEW)
        # =====================================================
        ctx = getattr(kernel, "last_ctx", None)

        if ctx and hasattr(ctx, "trace"):
            print("\n=== COGNITIVE TRACE ===")
            for step in ctx.trace.as_dict():
                print(step)

        print("\n-------------------------")        


if __name__ == "__main__":
    asyncio.run(run())