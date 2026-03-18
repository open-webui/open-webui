import asyncio
import aiohttp
from aiohttp import web

async def handle(request):
    response = web.StreamResponse()
    await response.prepare(request)
    for i in range(5):
        await response.write(b"data: a\n\n")
        await asyncio.sleep(0.1)
    await response.write(b"data: [DONE]\n\n")
    return response

async def main():
    app = web.Application()
    app.add_routes([web.get("/", handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 8080)
    await site.start()

    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:8080/") as r:
            print("iterating...")
            async for chunk in r.content:
                print(f"Got chunk: {chunk}")

    await runner.cleanup()

asyncio.run(main())