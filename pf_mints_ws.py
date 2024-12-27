import asyncio
import base64
import json
import struct
from time import sleep

import websockets
from construct import Struct, Padding, Int64ul, Flag, Bytes
from solders.pubkey import Pubkey  # type: ignore
from solders.pubkey import Pubkey  # type: ignore
from pump_fun_py.example_buy import buy_example
from pump_fun_py.example_sell import sell_example


WSS = "wss://mainnet.helius-rpc.com/?api-key="

trade = Struct(
    Padding(8),
    "mint" / Bytes(32),
    "solAmount" / Int64ul,
    "tokenAmount" / Int64ul,
    "isBuy" / Flag,
    "user" / Bytes(32),
    "timestamp" / Int64ul,
    "virtualSolReserves" / Int64ul,
    "virtualTokenReserves" / Int64ul
)


def buy_and_sell(mint_str: str):
    ret = buy_example(mint_str)
    if ret is None or ret == False:
        print("unable to buy, pass")
        return
    print(f"Bought {mint_str}, waiting 60 seconds before selling...")
    sleep(40)
    sell_example(mint_str)
    print(f"Sold {mint_str}")


def format_trade(parsed_data, txn_sig):
    try:
        return {
            "mint": str(Pubkey.from_bytes(bytes(parsed_data.mint))),
            "sol_amount": parsed_data.solAmount / 10**9,
            "token_amount": parsed_data.tokenAmount / 10**6,
            "is_buy": parsed_data.isBuy,
            "user": str(Pubkey.from_bytes(bytes(parsed_data.user))),
            "timestamp": parsed_data.timestamp,
            "virtual_sol_reserves": parsed_data.virtualSolReserves,
            "virtual_token_reserves": parsed_data.virtualTokenReserves,
            "txn_sig": txn_sig
        }
    except Exception as e:
        print(f"Error formatting trade data: {e}")
        return None

def parse_event_data(data_hex):
    try:
        data_bytes = bytes.fromhex(data_hex)
        offset = 8

        def read_length_prefixed_string(data, offset):
            try:
                length = struct.unpack('<I', data[offset:offset + 4])[0]
                offset += 4
                string_data = data[offset:offset + length]
                offset += length
                return string_data.decode('utf-8').strip('\x00'), offset
            except Exception as e:
                print(f"Error reading length-prefixed string: {e}")
                raise

        def read_pubkey(data, offset):
            try:
                pubkey_data = data[offset:offset + 32]
                offset += 32
                pubkey = str(Pubkey.from_bytes(pubkey_data))
                return pubkey, offset
            except Exception as e:
                print(f"Error reading pubkey: {e}")
                raise

        event_data = {}
        event_data['name'], offset = read_length_prefixed_string(data_bytes, offset)
        event_data['symbol'], offset = read_length_prefixed_string(data_bytes, offset)
        event_data['uri'], offset = read_length_prefixed_string(data_bytes, offset)
        event_data['mint'], offset = read_pubkey(data_bytes, offset)
        event_data['bonding_curve'], offset = read_pubkey(data_bytes, offset)
        event_data['user'], offset = read_pubkey(data_bytes, offset)

        return event_data
    except Exception as e:
        print(f"Error parsing event data: {e}")
        raise

async def logs_subscribe():
    try:
        async with websockets.connect(WSS, ping_interval=1200, ping_timeout=1800) as websocket:
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "logsSubscribe",
                "params": [
                    {"mentions": ["6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"]}, 
                    {"commitment": "processed"}
                ]
            }

            try:
                await websocket.send(json.dumps(request))
                print("Subscribed to logs...")
            except Exception as e:
                print(f"Error sending subscription request: {e}")
                return

            while True:
                try:
                    response = await websocket.recv()
                    log_data = json.loads(response)
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    continue
                except Exception as e:
                    print(f"Error receiving or processing response: {e}")
                    continue

                try:
                    result_value = log_data.get("params", {}).get("result", {}).get("value", {})
                    txn_sig = result_value.get("signature", "")
                except Exception as e:
                    print(f"Error extracting data from log response: {e}")
                    continue

                logs_list = log_data.get("params", {}).get("result", {}).get("value", {}).get("logs", [])

                logs = ''.join(logs_list)
                event_data = {}

                if "Instruction: InitializeMint2" in logs and "Program log: Instruction: Buy" in logs:
                    for log_entry in logs_list:
                        if "Program data: " in log_entry and not log_entry.startswith("Program data: vdt/"):
                            try:
                                program_data_base64 = log_entry.split("Program data: ")[1]
                                program_data_bytes = base64.b64decode(program_data_base64)
                                program_data_hex = program_data_bytes.hex()
                            except Exception as e:
                                print(f"Error decoding base64 program data: {e}")
                                continue
                            try:
                                event_data.update(parse_event_data(program_data_hex))
                            except Exception as e:
                                print(f"Error processing event data: {e}")
                        if "Program data: vdt/" in log_entry:
                            try:
                                program_data_base64 = log_entry.split("Program data: ")[1]
                                program_data_bytes = base64.b64decode(program_data_base64)
                            except Exception as e:
                                print(f"Error decoding base64 program data: {e}")
                                continue

                            try:
                                parsed_data = trade.parse(program_data_bytes)
                                trade_data = format_trade(parsed_data, txn_sig)
                                event_data.update(trade_data)
                            except Exception as e:
                                print(f"Error parsing or formatting trade data: {e}")
                    print(f"[*] Mint: {event_data.get('mint')}\tSol Amount: {event_data.get('sol_amount')}")
                    if event_data.get('sol_amount') > 2:
                        asyncio.create_task(buy_and_sell(event_data.get('mint')))
                    with open("./mints.csv", "a") as f:
                        # output the json data to a csv file
                        f.write(f"{event_data.get('mint')},"
                                f"{event_data.get('sol_amount')},"
                                f"{event_data.get('token_amount')},"
                                f"{event_data.get('is_buy')},"
                                f"{event_data.get('user')},"
                                f"{event_data.get('timestamp')},"
                                f"{event_data.get('virtual_sol_reserves')},"
                                f"{event_data.get('virtual_token_reserves')},"
                                f"{event_data.get('txn_sig')}\n"
                                )
    except Exception as e:
        print(f"Error in logs subscription: {e}")

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(logs_subscribe())
        except Exception as e:
            print(f"Unexpected error in main event loop: {e}")
