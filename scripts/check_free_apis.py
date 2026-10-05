"""Test configured free providers without printing credentials or exception URLs."""
import asyncio
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv()


async def main():
    import httpx
    from common.geoapify import city_places
    if os.getenv("GEOAPIFY_API_KEY"):
        async with httpx.AsyncClient() as client:
            for kind, categories in [("activities", "tourism.sights,entertainment.museum,leisure.park")]:
                result = await city_places(client, "Rome", categories, 10000)
                print("GEOAPIFY", kind, "OK", len(result[1])) if result else print("GEOAPIFY", kind, "FAILED (credentials, quota or network)")
    else:
        print("GEOAPIFY: SKIPPED - missing GEOAPIFY_API_KEY")
    if os.getenv("GEMINI_API_KEY"):
        from google import genai
        from google.genai import types
        try:
            with genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=types.HttpOptions(timeout=20000)) as client:
                result = client.models.generate_content(model=os.getenv("VOYAGEPLUS_MODEL", "gemini/gemini-3.1-flash-lite").removeprefix("gemini/"), contents="Respond only with OK.")
                print("GEMINI: OK", bool(result.text))
        except Exception as error:
            print("GEMINI: FAILED", type(error).__name__, "code", getattr(error, "code", None))
    else:
        print("GEMINI: SKIPPED - missing GEMINI_API_KEY")


if __name__ == "__main__":
    asyncio.run(main())
