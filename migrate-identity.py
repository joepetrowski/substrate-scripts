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

import os
from substrateinterface import SubstrateInterface, Keypair
from substrateinterface.exceptions import SubstrateRequestException

# Config

# Set a limit. E.g. `limit = 5` will only migrate 5 identities. `None` will do all.
limit = None
# Actually submit extrinsics to the chain. If `False`, it will just log stuff to console.
submit = False
# The chain to connect to.
chain = SubstrateInterface(
	#url="ws://127.0.0.1:9944",
	# Using the public endpoint can get you rate-limited.
	# Westend
	# url="wss://westend-rpc.polkadot.io",
	# Kusama
	# url="wss://kusama-try-runtime-node.parity-chains.parity.io:443",
	# Polkadot
	url="wss://polkadot-try-runtime-node.parity-chains.parity.io:443",
	# Or use some external node:
	# url="wss://rococo-try-runtime-node.parity-chains.parity.io:443"
)

print(f"Connected to {chain.name}: {chain.chain} v{chain.version}")

sender_uri = os.getenv('SENDER_URI', '//Alice')
sender = Keypair.create_from_uri(sender_uri)
print(f"Using sender account {sender.ss58_address}")

decimals = chain.token_decimals or 0

def main():
	unmigrated = identities()
	if len(unmigrated) == 0:
		print("No identities to migrate - finish")
		return

	subs = get_subs()

	id_dep = id_deposit()
	sub_dep = sub_deposit()
	ed = 10_000_000_000 # 1 DOT

	print(f"Migrating {len(unmigrated)} identities")

	count = 0

	for user in unmigrated:
		# First, check their balance.
		balance = get_balance(user)

		# Calculate the amount they will need.
		num_subs = subs_of(user, subs)
		amount_needed = id_dep + (num_subs * sub_dep)

		# If they need funding, construct a transfer call.
		transfer_call = None
		if balance < amount_needed:
			print(f"User {user} has low balance:")
			print(f"    Balance:  {balance / 10**decimals}")
			print(f"    Required: {amount_needed / 10**decimals}")
			needed = max(ed, amount_needed - balance)
			transfer_call = balance_transfer(user, needed)

		reap_call = reap(user)

		if not transfer_call:
			call = reap_call
		else:
			call = batch_all_calls([transfer_call, reap_call])

		extrinsic = chain.create_signed_extrinsic(call, keypair=sender)

		print(f'Sending call for {user}')

		if submit:
			try:
				receipt = chain.submit_extrinsic(extrinsic, wait_for_inclusion=True)
				print(f"Extrinsic included in block {receipt.block_hash}: "
					f"paid {(receipt.total_fee_amount or 0) / 10**decimals} {chain.token_symbol}")
			except SubstrateRequestException as e:
				print(f"Failed to submit extrinsic: {e}")
				raise e

		count += 1
		if count % 100 == 0:
			print(f"\n\nMigrated {count} identities\n\n")
		if limit and count > limit:
			break

# Get the next `page_size` identities to be migrated.
def identities():
	print(f'Fetching the identities to be migrated')
	query = chain.query_map('Identity', 'IdentityOf')

	accs = []
	for (account, data) in query:
		accs.append(account.value)
	return accs

# Fetch the entire map of sub accounts.
def get_subs():
	query = chain.query_map('Identity', 'SubsOf')
	return query

# Force return an int so as not to return None
def subs_of(who, map) -> int:
	for acc, ii in map:
		if who == acc:
			return len(ii.value[1])
	return 0

# Get the balance of a user `who`.
def get_balance(who):
	query = chain.query("System", "Account", [who])
	return query.value['data']['free'] + query.value['data']['reserved']

# Construct a balance transfer call.
def balance_transfer(who, amount):
	call = chain.compose_call(
		call_module='Balances',
		call_function='transfer_keep_alive',
		call_params={
			'dest': who,
			'value': amount
		}
	)
	return call

# Construct a `reap_identity` call.
def reap(who):
	call = chain.compose_call(
		call_module='IdentityMigrator',
		call_function='reap_identity',
		call_params={
			'who': who,
		}
	)
	return call

# Batch an array of `calls` using `batch_all`.
def batch_all_calls(calls: list):
	call = chain.compose_call(
		call_module='Utility',
		call_function='batch_all',
		call_params={
			'calls': calls,
		}
	)
	return call

# Get the deposit rate on a system parachain.
def para_deposit(items, size):
	units = 10_000_000_000
	dollars = units
	cents = dollars / 100
	millicents = cents / 1_000
	return (items * 20 * dollars + size * 100 * millicents) / 100

# Get the max ID deposit on the People chain.
def id_deposit():
	items = 1
	# min is 17, but this param has such a small effect it's not even worth looking it up for each
	# person
	max_size = 318
	return para_deposit(items, max_size)

# Get the deposit required per sub account on the People chain.
def sub_deposit():
	items = 1
	size = 53
	return para_deposit(items, size)

if __name__ == "__main__":
	main()
