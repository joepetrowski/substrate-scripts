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

chain = SubstrateInterface(
	#url="ws://127.0.0.1:9944",
	# Using the public endpoint can get you rate-limited.
	# Westend
	# url="wss://westend-rpc.polkadot.io",
	# Kusama
	url="wss://kusama-try-runtime-node.parity-chains.parity.io:443",
	# Or use some external node:
	# url="wss://rococo-try-runtime-node.parity-chains.parity.io:443"
)

print(f"Connected to {chain.name}: {chain.chain} v{chain.version}")

wait_for_inclusion = True
sender_uri = os.getenv('SENDER_URI', '//Alice')
sender = Keypair.create_from_uri(sender_uri)
print(f"Using sender account {sender.ss58_address}")

weight_second = 1e12
decimals = chain.token_decimals or 0

# Kusama "problems"
need_funding = [
	'Hw4J3VBtCGnHufxTkDJHvsWxS8iKE7LyBKH5pYA6MNQGxAJ',
	'DAhmGRNP9tSxYn3x9JmNSeqm6cYwBx2vLrGBF1i1Pp1Awi8',
	'F7sLQmzKw2CyKr2krKQRQZL1y4E7FzFXAbvV8KrzKeb5HQX',
	'EZv3htNfDpYt6m42xBaEbLr2Y2ZcPjHvY9y6tvZEcWBmefJ',
	'EB9N9Qyej8zcCVmRQaPRTTdZFHvnK3o7xKEnus7mJ5ErmGC',
	'DwbHothibGR4fuMfuKh6zBhUSTcgwHhZ5xxfmDC61h9B3U7',
	'ESJv66mEU2a2r6gmmUYgjwZFU59TMPpEbcmdPgHfXg6qaZb',
	'GJ9CvUDXGKV51iZBawhQ9d18oQNuefDg1mSg5vW6NtGTvDt',
	'CwhoqP9qY3ZBRM5ZYCpBzz5tYZEYULVQrPPc98xr5HbH555',
	'DV4mtkWPzTwnFNM5LvRJUZTNXW23rGji2N8VQdGHUDzZcjX',
	'FvgbJ5qNw3jpV5KN7yNZ9ZeBwC6DdrqsBKonuTVUgoB1rjk',
	'HtKtEzu9g6FwAFfyWsUEG4pTPEdD1rGH1Jyxe8WvHNLj8VY',
	'J3dMirndvThJKJT7vWuUgh5tqmzRWfPA9YhEANBZG5SVcoy',
	'FPJxsupc3LWLjHfL9nh64dmVKvXvGGpdFseqFyPVBNR8wMa',
	'CgGKH1dsPgJkQ3caFsnDtMUWUqVJKEpRt1ekM5RDW4UrYhP',
	'FP7Tvuid4tf1aeX9oGLedshiHSaFEQtEMSEDAcDExG8H3GA',
	'CzJSFEuiLHD1defThphhyXEd3AwxBMPpZvUbqnzpFBx4z4y',
	'GS8cNk9ysUwoBp2ibWYNzjDvR9R4f9iyKoYdnDBbdP1ZDbn',
	'GeXF6s9yv7UyhKzLMkpSZwoVwhDrN3xcBamwfRg6zphR6Fy',
	'J6fWu1bGYWSBSznpdUvcj1pvidEjsD4Pii9D1eyJgWNdzJF',
	'HvRV8gaVwfXHsV3zeBh8N6uK8xnvTfQPupXwyehyfGmzd5m',
	'Gek2uCr3kWqdt8eSaYzE1GxNn3b1RB1FYgzyQuKhhJ63X7r',
	'FP1Qh2nTBr7RvXxmj5AUZ96rMDHEhTvqKYEAyAWgQKDCMau',
	'DrPFcfMyzRM3KtqEvZZv22qUQTEDRSUNDPuJPPT5vS4pq6j',
	'GHTDNsavESZRBVi6iEWJZQV1uPynsvLQ4v9wLGTM192FFoq',
	'J6R1Ds3WfbZ3nm1Jn8N4jssz2Cj9QPyUpECssnKAPMfycFh',
]

def main():
	unmigrated = identities()
	if len(unmigrated) == 0:
		print("No identities to migrate - finish")
		return

	subs = get_subs()

	# For Kusama
	id_dep = 7_000_000_000
	sub_dep = 7_000_000_000

	print(f"Migrating {len(unmigrated)} identities")

	count = 0

	for user in unmigrated:
		# if user in errors:
		# 	print(f"skipping {user}")
		# 	continue
		#
		# TODO: Check if extrinsic success, if false then add user to this list and try again.
		if user in need_funding:
			num_subs = subs_of(user, subs)
			amount = 0
			
			if num_subs > 0:
				amount += (id_dep + sub_dep)
			else:
				amount += id_dep
			
			transfer_call = balance_transfer(user, amount)
			reap_call = reap(user)
			batch = batch_all_calls([transfer_call, reap_call])

			extrinsic = chain.create_signed_extrinsic(call=batch, keypair=sender)
		else:
			reap_call = reap(user)
			extrinsic = chain.create_signed_extrinsic(call=reap_call, keypair=sender)
		
		# print(f'{extrinsic}')
		print(f'Sending call for {user}')

		try:
			receipt = chain.submit_extrinsic(extrinsic, wait_for_inclusion)
			print(f"Extrinsic included in block {receipt.block_hash}: "
				f"paid {(receipt.total_fee_amount or 0) / 10**decimals} {chain.token_symbol}")
		except SubstrateRequestException as e:
			print(f"Failed to submit extrinsic: {e}")
			raise e

		count += 1
		if count % 100 == 0:
			print(f"\n\nMigrated {count} identities\n\n")
		# if count > 0:
		# 	break

# Get the next `page_size` identities to be migrated.
def identities():
	print(f'Fetching the identities to be migrated')
	query = chain.query_map('Identity', 'IdentityOf')

	accs = []
	for (account, data) in query:
		accs.append(account.value)
	return accs

def get_subs():
	query = chain.query_map('Identity', 'SubsOf')
	return query

# Force return an int so as not to return None
def subs_of(who, map) -> int:
	for acc, ii in map:
		if who == acc:
			return len(ii.value[1])
	return 0

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

def reap(who):
	call = chain.compose_call(
		call_module='IdentityMigrator',
		call_function='reap_identity',
		call_params={
			'who': who,
		}
	)
	return call

def batch_all_calls(calls: list):
	call = chain.compose_call(
		call_module='Utility',
		call_function='batch_all',
		call_params={
			'calls': calls,
		}
	)
	return call

if __name__ == "__main__":
	main()
