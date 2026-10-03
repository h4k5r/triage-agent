import asyncio

async def forward(reader, writer):
    try:
        r, w = await asyncio.open_connection('127.0.0.1', 11434)
    except Exception:
        writer.close()
        return

    async def pipe(src, dst):
        try:
            while data := await src.read(65536):
                dst.write(data)
                await dst.drain()
        except Exception:
            pass
        finally:
            try:
                dst.close()
            except Exception:
                pass

    await asyncio.gather(pipe(reader, w), pipe(r, writer))

async def main():
    server = await asyncio.start_server(forward, '0.0.0.0', 11435)
    print("Ollama bridge listening on 0.0.0.0:11435 -> 127.0.0.1:11434", flush=True)
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
