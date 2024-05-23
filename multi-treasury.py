from substrateinterface import SubstrateInterface

chain = SubstrateInterface(
	# Local
	#url="ws://127.0.0.1:9944",

	# Westend
	# url="wss://westend-rpc.polkadot.io",

	# Kusama
	# url="wss://kusama-try-runtime-node.parity-chains.parity.io:443",

	# Polkadot
	url="wss://polkadot-rpc.dwellir.com:443",
)

print(f"Connected to {chain.name}: {chain.chain} v{chain.version}")

decimals = chain.token_decimals
number_of_payments = 48
time_between_payments = 30 * 14_400 # 30 days
governance_track_time = 28 * 14_400 # 28 days
amount_of_each = 200_000 * 10**decimals
# 14WjkhgfbD98TA2SuJiqrnhhPCmpfCFVtQ46Zcr4DEAwegQi
beneficiary = "0x9b62bcf47bb081dc8ecdf2d205b84d7c37261d3b5713b8e303b43537ca3a18ac"

native_asset = {
	'location': {'parents': 0, 'interior': { 'X1': [{'Parachain': 1000}] }},
	'asset_id': {'parents': 1, 'interior': 'Here'}
}

beneficiary_as_location = {
	'V4': {
		'parents': 0,
		'interior': { 'X1': [{ 'AccountId32': { 'id': beneficiary, 'network': None } }] }
	}
}

def main():
	calls = []
	block = chain.get_block()
	block_number = block['header']['number']

	first_call = chain.compose_call(
		call_module='Treasury',
		call_function='spend',
		call_params={
			'asset_kind': {'V4': native_asset },
			'amount': amount_of_each,
			'beneficiary': beneficiary_as_location,
			'valid_from': None
		}
	)
	calls.append(first_call)

	# Loop through to make more calls
	for ii in range(1, number_of_payments):
		# First payment is valid immediately (block_number + governance_track_time).
		# Subsequent payments are valid in `time_between_payout` intervals after.
		valid_from = block_number + governance_track_time + (ii * time_between_payments)
		call = chain.compose_call(
			call_module='Treasury',
			call_function='spend',
			call_params={
				'asset_kind': {'V4': native_asset },
				'amount': amount_of_each,
				'beneficiary': beneficiary_as_location,
				'valid_from': valid_from
			}
		)
		# print(call)
		calls.append(call)

	call = chain.compose_call(
		call_module='Utility',
		call_function='batch',
		call_params={
			'calls': calls,
		}
	)
	scale_extrinsic = chain.encode_scale("GenericCall", call)

	print('\nThe call to submit is:\n')
	print(scale_extrinsic)

if __name__ == "__main__":
	main()
