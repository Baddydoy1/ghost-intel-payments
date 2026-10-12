import json
import os
from decimal import Decimal

import requests
from web3 import Web3

API_BASE = os.getenv("API_BASE", "https://api.a2a.family")
ROBINHOOD_RPC_URL = os.getenv("ROBINHOOD_RPC_URL", "https://rpc.robinhood.chain")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
USDG_ADDRESS = os.getenv("USDG_ADDRESS")
AGENT_WALLET = os.getenv("AGENT_WALLET")

if not PRIVATE_KEY:
    raise RuntimeError("PRIVATE_KEY is required")
if not USDG_ADDRESS:
    raise RuntimeError("USDG_ADDRESS is required")
if not AGENT_WALLET:
    raise RuntimeError("AGENT_WALLET is required")

w3 = Web3(Web3.HTTPProvider(ROBINHOOD_RPC_URL))
if not w3.is_connected():
    raise RuntimeError(f"Could not connect to {ROBINHOOD_RPC_URL}")

account = w3.eth.account.from_key(PRIVATE_KEY)

USDG_ABI = [
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
        "name": "transfer",
        "outputs": [{"name": "success", "type": "bool"}],
        "type": "function",
    },
]

usdg_contract = w3.eth.contract(address=Web3.to_checksum_address(USDG_ADDRESS), abi=USDG_ABI)


def send_usdg(recipient: str, amount_usdg: str) -> str:
    """Send USDG to recipient and return tx hash."""
    decimals = usdg_contract.functions.decimals().call()
    amount = Decimal(str(amount_usdg))
    amount_units = int((amount * (Decimal(10) ** decimals)).to_integral_value())
    recipient_addr = Web3.to_checksum_address(recipient)

    tx_func = usdg_contract.functions.transfer(recipient_addr, amount_units)
    nonce = w3.eth.get_transaction_count(account.address)

    try:
        gas_estimate = tx_func.estimate_gas({"from": account.address})
    except Exception:
        gas_estimate = 150000

    gas_limit = max(int(gas_estimate * 1.2), 100000)
    latest = w3.eth.get_block("latest")
    if latest.get("baseFeePerGas") is not None:
        tx = tx_func.build_transaction(
            {
                "from": account.address,
                "nonce": nonce,
                "gas": gas_limit,
                "maxFeePerGas": w3.to_wei("2", "gwei"),
                "maxPriorityFeePerGas": w3.to_wei("1", "gwei"),
                "chainId": w3.eth.chain_id,
            }
        )
    else:
        tx = tx_func.build_transaction(
            {
                "from": account.address,
                "nonce": nonce,
                "gas": gas_limit,
                "gasPrice": w3.to_wei("2", "gwei"),
                "chainId": w3.eth.chain_id,
            }
        )

    signed = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return w3.to_hex(tx_hash)


def handle_x402_challenge(response, payment_payload=None):
    """Parse a 402 Payment Required response and pay the required amount in USDG."""
    try:
        payload = response.json()
    except Exception:
        payload = {}

    payment = payload.get("payment") or payment_payload or {}
    required_amount = payment.get("amount") or "0.01"
    required_recipient = payment.get("recipient") or AGENT_WALLET
    asset = (payment.get("asset") or "USDG").upper()

    if asset != "USDG":
        raise RuntimeError(f"Unsupported x402 asset: {asset}")

    tx_hash = send_usdg(required_recipient, required_amount)
    return {
        "tx_hash": tx_hash,
        "status": "paid",
        "amount": required_amount,
        "recipient": required_recipient,
    }


def hire_agent(task_payload):
    """Create a task or hire request. If the API issues a 402 challenge, pay and retry."""
    url = f"{API_BASE}/hire"
    r = requests.post(url, json=task_payload, timeout=30)

    if r.status_code == 402:
        payment_info = handle_x402_challenge(r)
        headers = {"X-Payment-Hash": payment_info["tx_hash"]}
        retry = requests.post(url, json=task_payload, headers=headers, timeout=30)
        retry.raise_for_status()
        return retry

    r.raise_for_status()
    return r


if __name__ == "__main__":
    payload = {
        "agent": "a2a-agent",
        "task": "summarize this file or complete a job",
        "metadata": {
            "source": "ghost-intel-payments",
            "wallet": AGENT_WALLET,
        },
    }

    response = hire_agent(payload)
    print(response.status_code)
    print(response.text)
