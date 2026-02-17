#!/usr/bin/env python3
"""
SDF COM Client - SSH connection and COM chat automation for sdf.org
"""

import asyncio
import asyncssh
import sys
import argparse


class SDFComClient:
    """Client for connecting to SDF.org and operating COM chat"""

    def __init__(self, username: str, password: str, host: str = "sdf.org"):
        self.username = username
        self.password = password
        self.host = host
        self.conn = None
        self.process = None

    async def connect(self):
        """Establish SSH connection to SDF"""
        self.conn = await asyncssh.connect(
            self.host,
            username=self.username,
            password=self.password,
            known_hosts=None  # Accept new host keys
        )
        return self.conn

    async def start_com(self):
        """Start COM chat program"""
        if not self.conn:
            raise RuntimeError("Not connected. Call connect() first.")

        self.process = await self.conn.create_process(
            'com',
            term_type='xterm-256color'
        )
        return self.process

    async def send_command(self, command: str, wait_for_output: bool = True):
        """Send a command to COM and optionally wait for output"""
        if not self.process:
            raise RuntimeError("COM not started. Call start_com() first.")

        self.process.stdin.write(command + '\n')
        await self.process.stdin.drain()

        if wait_for_output:
            # Give COM time to respond
            await asyncio.sleep(0.5)
            output = await self._read_output()
            return output
        return None

    async def _read_output(self, timeout: float = 2.0):
        """Read available output from COM"""
        output = ""
        try:
            while True:
                line = await asyncio.wait_for(
                    self.process.stdout.readline(),
                    timeout=0.3
                )
                if line:
                    output += line
                else:
                    break
        except asyncio.TimeoutError:
            pass
        return output

    async def get_room_list(self):
        """List all available rooms (l command)"""
        return await self.send_command('l')

    async def get_user_list(self):
        """List users in current room (w command)"""
        return await self.send_command('w')

    async def goto_room(self, room_name: str):
        """Go to a specific room (g command)"""
        self.process.stdin.write('g\n')
        await self.process.stdin.drain()
        await asyncio.sleep(0.3)

        self.process.stdin.write(room_name + '\n')
        await self.process.stdin.drain()
        await asyncio.sleep(0.5)

        return await self._read_output()

    async def say(self, message: str):
        """Say something in the current room (space + message)"""
        # Space enters input mode
        self.process.stdin.write(' ')
        await self.process.stdin.drain()
        await asyncio.sleep(0.2)

        # Type the message
        self.process.stdin.write(message + '\n')
        await self.process.stdin.drain()
        await asyncio.sleep(0.5)

        return await self._read_output()

    async def review_history(self, lines: int = 18):
        """Review room history (r or R command)"""
        if lines <= 18:
            return await self.send_command('r')
        else:
            self.process.stdin.write('R\n')
            await self.process.stdin.drain()
            await asyncio.sleep(0.3)

            self.process.stdin.write(str(lines) + '\n')
            await self.process.stdin.drain()
            await asyncio.sleep(0.5)

            return await self._read_output()

    async def peek_room(self, room_name: str, lines: int = 18):
        """Peek into another room (p command)"""
        self.process.stdin.write(f'p{room_name}\n')
        await self.process.stdin.drain()
        await asyncio.sleep(0.5)

        if lines != 18:
            self.process.stdin.write(str(lines) + '\n')
            await self.process.stdin.drain()
            await asyncio.sleep(0.3)

        return await self._read_output()

    async def send_private(self, user: str, message: str, room: str = None):
        """Send private message (s command): suser@host [room]"""
        if room:
            cmd = f's{user} {room}'
        else:
            cmd = f's{user}'

        self.process.stdin.write(cmd + '\n')
        await self.process.stdin.drain()
        await asyncio.sleep(0.3)

        self.process.stdin.write(message + '\n')
        await self.process.stdin.drain()
        await asyncio.sleep(0.5)

        return await self._read_output()

    async def emote(self, action: str):
        """Send emote (e command)"""
        self.process.stdin.write('e\n')
        await self.process.stdin.drain()
        await asyncio.sleep(0.3)

        self.process.stdin.write(action + '\n')
        await self.process.stdin.drain()
        await asyncio.sleep(0.5)

        return await self._read_output()

    async def get_help(self):
        """Show COM help (h command)"""
        return await self.send_command('h')

    async def query_idle(self):
        """Query user idle times (I command)"""
        return await self.send_command('I')

    async def who_other_room(self, room_name: str):
        """Who is in another room (W command)"""
        self.process.stdin.write(f'W{room_name}\n')
        await self.process.stdin.drain()
        await asyncio.sleep(0.5)
        return await self._read_output()

    async def quit(self):
        """Quit COM (q command)"""
        if self.process:
            await self.send_command('q', wait_for_output=False)
            self.process.close()
            await self.process.wait()
            self.process = None

    async def disconnect(self):
        """Close SSH connection"""
        if self.process:
            await self.quit()
        if self.conn:
            self.conn.close()
            await self.conn.wait_closed()
            self.conn = None


async def interactive_session(username: str, password: str):
    """Run an interactive COM session"""
    client = SDFComClient(username, password)

    try:
        print(f"Connecting to SDF as {username}...")
        await client.connect()
        print("Connected!")

        print("Starting COM...")
        await client.start_com()
        print("COM started! Reading initial output...")

        # Read initial COM output
        await asyncio.sleep(1)
        output = await client._read_output(timeout=3.0)
        print(output)

        print("\n=== COM Interactive Mode ===")
        print("Commands: /w (who), /l (list rooms), /g <room> (goto), /s <msg> (say)")
        print("          /r (review), /p <room> (peek), /q (quit)")
        print("Or type raw COM commands directly\n")

        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, "com> "
                )

                if user_input.startswith('/q'):
                    break
                elif user_input.startswith('/w'):
                    output = await client.get_user_list()
                    print(output)
                elif user_input.startswith('/l'):
                    output = await client.get_room_list()
                    print(output)
                elif user_input.startswith('/g '):
                    room = user_input[3:].strip()
                    output = await client.goto_room(room)
                    print(output)
                elif user_input.startswith('/s '):
                    msg = user_input[3:]
                    output = await client.say(msg)
                    print(output)
                elif user_input.startswith('/r'):
                    output = await client.review_history()
                    print(output)
                elif user_input.startswith('/p '):
                    room = user_input[3:].strip()
                    output = await client.peek_room(room)
                    print(output)
                elif user_input.startswith('/h'):
                    output = await client.get_help()
                    print(output)
                elif user_input.startswith('/I'):
                    output = await client.query_idle()
                    print(output)
                elif user_input.startswith('/e '):
                    action = user_input[3:]
                    output = await client.emote(action)
                    print(output)
                elif user_input.startswith('/W '):
                    room = user_input[3:].strip()
                    output = await client.who_other_room(room)
                    print(output)
                else:
                    # Send raw command to COM
                    output = await client.send_command(user_input)
                    if output:
                        print(output)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

    finally:
        print("\nDisconnecting...")
        await client.disconnect()
        print("Disconnected!")


def main():
    parser = argparse.ArgumentParser(description='SDF COM Client')
    parser.add_argument('username', help='SDF username')
    parser.add_argument('password', help='SDF password')
    parser.add_argument('--command', '-c', help='Single command to execute')
    parser.add_argument('--room', '-r', help='Room to join')
    parser.add_argument('--message', '-m', help='Message to send')

    args = parser.parse_args()

    if args.command or args.room or args.message:
        # Single command mode
        asyncio.run(run_single_command(args))
    else:
        # Interactive mode
        asyncio.run(interactive_session(args.username, args.password))


async def run_single_command(args):
    """Execute a single command and exit"""
    client = SDFComClient(args.username, args.password)

    try:
        await client.connect()
        await client.start_com()
        await asyncio.sleep(1)

        # Read initial output
        await client._read_output(timeout=2.0)

        if args.room:
            output = await client.goto_room(args.room)
            print(output)

        if args.message:
            output = await client.say(args.message)
            print(output)

        if args.command:
            output = await client.send_command(args.command)
            print(output)

    finally:
        await client.disconnect()


if __name__ == '__main__':
    main()
