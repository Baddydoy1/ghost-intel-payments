# ghost-intel-payments

A small Python utility for sending USDG on Robinhood Chain using Web3.

## Overview

This repository contains a simple ERC-20 transfer helper that:

- connects to the Robinhood Chain RPC endpoint
- loads your private key from an environment variable
- reads the USDG token contract address from an environment variable
- builds and sends a token transfer transaction
- waits for confirmation and prints the transaction hash

## Security

Never commit a real private key. This project expects secrets to be provided through environment variables or a local `.env` file that is ignored by git.

## Setup

1. Clone the repository.
2. Create a virtual environment if desired.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Example:

```env
ROBINHOOD_RPC_URL=https://rpc.robinhood.chain
PRIVATE_KEY=your_private_key_here
USDG_ADDRESS=0xYOUR_USDG_CONTRACT_ADDRESS
```

5. Run the script:

```bash
python send_usdg.py 0xRecipientAddress 25.50
```

## Example use

```bash
python send_usdg.py 0x1234567890abcdef1234567890abcdef12345678 12.34
```

## Notes

- The script uses an ERC-20 `transfer` call and sends the transaction from your wallet account.
- Gas is paid in the chain’s native currency.
- You should verify the token contract address and decimals for the exact USDG deployment you are using.
- If the token has a different decimals value than 6, the code will automatically read it from the contract.

## Files

- `send_usdg.py` — main transfer helper
- `.env.example` — sample environment configuration
- `requirements.txt` — Python dependencies
- `.gitignore` — ignores secrets and local environment files
