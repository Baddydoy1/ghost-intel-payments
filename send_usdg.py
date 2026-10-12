from decimal import Decimal, InvalidOperation
import os
import sys

from web3 import Web3
from web3.exceptions import ContractLogicError

RPC_URL = os.getenv("ROBINHOOD_RPC_URL", "https://rpc.robinhood.chain")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
USDG_ADDRESS = os.getenv("USDG_ADDRESS")

if not PRIVATE_KEY:
    raise SystemExit("Missing PRIVATE_KEY environment variable.")

if not USDG_ADDRESS:
    raise SystemExit("Missing USDG_ADDRESS environment variable.")

w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    raise SystemExit(f"Unable to connect to Robinhood Chain RPC at {RPC_URL}")

account = w3.eth.account.from_key(PRIVATE_KEY)

USDG_ABI = [
    {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "success", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "remaining", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "success", "type": "bool"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_from", "type": "address"}, {"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transferFrom", "outputs": [{"name": "success", "type": "bool"}], "type": "function"},
    {"anonymous": False, "inputs": [{"indexed": True, "name": "from", "type": "address"}, {"indexed": True, "name": "to", "type": "address"}, {"indexed": False, "name": "value", "type": "uint256"}], "name": "Transfer", "type": "event"},
]

usdg_contract = w3.eth.contract(address=Web3.to_checksum_address(USDG_ADDRESS), abi=USDG_ABI)


def to_token_units(amount: str, decimals: int) -> int:
    try:
        amount_decimal = Decimal(amount)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid USDG amount: {amount!r}") from exc

    multiplier = Decimal(10) ** decimals
    return int((amount_decimal * multiplier).to_integral_value())


def send_usdg_payment(recipient_address: str, amount_usdg: str) -> str:
    recipient = Web3.to_checksum_address(recipient_address)
    decimals = usdg_contract.functions.decimals().call()
    amount_in_units = to_token_units(amount_usdg, decimals)

    tx_function = usdg_contract.functions.transfer(recipient, amount_in_units)
    nonce = w3.eth.get_transaction_count(account.address)

    try:
        gas_estimate = tx_function.estimate_gas({"from": account.address})
    except ContractLogicError:
        gas_estimate = 150000

    gas_limit = max(int(gas_estimate * 1.2), 100000)

    tx = tx_function.build_transaction(
        {
            "from": account.address,
            "nonce": nonce,
            "gas": gas_limit,
            "maxFeePerGas": w3.to_wei("2", "gwei"),
            "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
            "chainId": w3.eth.chain_id,
        }
    )

    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    tx_hex = w3.to_hex(tx_hash)

    print(f"[*] Sent {amount_usdg} USDG to {recipient}")
    print(f"[*] Transaction Hash: {tx_hex}")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"[+] Confirmed in block {receipt['blockNumber']}")
    return tx_hex


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python send_usdg.py <recipient_address> <amount_usdg>")
        sys.exit(1)

    recipient = sys.argv[1]
    amount = sys.argv[2]
    send_usdg_payment(recipient, amount)
