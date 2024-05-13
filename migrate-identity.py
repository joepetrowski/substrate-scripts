"""
SPDX-License-Identifier: GPL-3.0-only

This script runs migration for the identity pallet for:
	<https://github.com/paritytech/polkadot-sdk/pull/1814>

Install the dependency:
	pip install substrate-interface
Set the env variable `SENDER_URI` and run:
	python3 migrate-identity.py
"""

"""
The batch size for each call to `reap_identity`.
It is set to a small value such that in case of a bug, the script wont burn
through a lot of funds.
"""

import time
import os
from substrateinterface import SubstrateInterface, Keypair
from substrateinterface.exceptions import SubstrateRequestException

chain = SubstrateInterface(
	#url="ws://127.0.0.1:9944",
	# Using the public endpoint can get you rate-limited.
	# Westend
	# url="wss://westend-rpc.polkadot.io",
	# Kusama
	url="wss://kusama-people-rpc.polkadot.io",
	# Or use some external node:
	# url="wss://rococo-try-runtime-node.parity-chains.parity.io:443"
)

print(f"Connected to {chain.name}: {chain.chain} v{chain.version}")

wait_for_inclusion = False
sender_uri = os.getenv('SENDER_URI', '//Alice')
sender = Keypair.create_from_uri(sender_uri)
print(f"Using sender account {sender.ss58_address}")

weight_second = 1e12
decimals = chain.token_decimals or 0

def main():
	unmigrated = identities()
	if len(unmigrated) == 0:
		print("No identities to migrate - finish")
		return

	print(f"Migrating {len(unmigrated)} identities")

	for user in unmigrated:
		call = chain.compose_call(
			call_module='IdentityMigrator',
			call_function='reap_identity',
			call_params={
				'who': user,
			}
		)
		extrinsic = chain.create_signed_extrinsic(call=call, keypair=sender)
		# print(f'{extrinsic}')
		print(f'Sending call for {user}')

		try:
			receipt = chain.submit_extrinsic(extrinsic, wait_for_inclusion)
			print(f"Extrinsic included in block {receipt.block_hash}: "
				f"consumed {receipt.weight['ref_time'] / weight_second} seconds of weight and "
				f"paid {(receipt.total_fee_amount or 0) / 10**decimals} {chain.token_symbol}")
			# Don't totally spam the chain
			if not wait_for_inclusion:
				time.sleep(1)
		except SubstrateRequestException as e:
			print(f"Failed to submit extrinsic: {e}")
			raise e

# Get the next `page_size` identities to be migrated.
def identities():
	print(f'Fetching the identities to be migrated')
	query = chain.query_map('Identity', 'IdentityOf')

	accs = []
	for (account, data) in query:
		accs.append(account.value)
	return accs

if __name__ == "__main__":
	main()
