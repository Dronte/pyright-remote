import argparse
import asyncio
import logging

logger = logging


class PortListner:
    def start(self, loop, port):
        self.port = port
        coro = asyncio.start_server(self.accept_server_connection, 'localhost', port)
        self.reader = None
        self.writer = None

        self.connected = asyncio.Event()
        return coro

    async def accept_server_connection(self, reader, writer):
        logger.info('Client connected on port %d', self.port)
        self.reader = reader
        self.writer = writer
        self.connected.set()

    def reset(self):
        self.reader = None
        self.writer = None
        self.connected.clear()

    def reset_if_need(self):
        if (
            self.reader is not None and self.reader.at_eof()
            or self.writer is not None and self.writer.is_closing()
        ):
            self.reset()


async def pipe(source, destination):
    try:
        while not source.reader.at_eof():
            data = await source.reader.read(2048)
            logger.debug('%d -> %d: %s', source.port, destination.port, data)
            destination.writer.write(data)
    except Exception as e:
        logger.exception(e)


async def async_main(loop, args):
    server = PortListner()
    await server.start(loop, args.server_port)
    client = PortListner()
    await client.start(loop, args.client_port)
    while True:
        await server.connected.wait()
        await client.connected.wait()
        client_to_server = loop.create_task(pipe(client, server))
        server_to_client = loop.create_task(pipe(server, client))
        await asyncio.wait(
            (client_to_server, server_to_client),
            return_when=asyncio.FIRST_COMPLETED
        )
        if not client_to_server.done():
            client_to_server.cancel()

        if not server_to_client.done():
            server_to_client.cancel()
        server.reset_if_need()
        client.reset_if_need()
        logging.info('Reconnecting pipe')


def get_argparser():
    argparser = argparse.ArgumentParser(description='Simple tcp pipe proxy')
    argparser.add_argument('--server-port', type=int, required=True, help='Port, the server will connect to')
    argparser.add_argument('--client-port', type=int, required=True, help='Port, the client will connect to')
    argparser.add_argument('--log-level', default='INFO', help='Log level. DEBUG will log transfered data.')
    return argparser


def setup_logging(args):
    logging.basicConfig(
        format='%(asctime)s - %(message)s',
        level=logging.getLevelName(args.log_level.upper())
    )


async def main():
    argparser = get_argparser()
    args = argparser.parse_args()
    setup_logging(args)
    loop = asyncio.get_running_loop()
    await async_main(loop, args)


if __name__ == '__main__':
    asyncio.run(main())
