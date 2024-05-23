"""
SPDX-License-Identifier: GPL-3.0-only

Compare that the Kusama identity pallet's storage `IdentityOf` is the
same as on the Kusama people chain.
"""

import json
import os
from substrateinterface import SubstrateInterface, Keypair
from substrateinterface.exceptions import SubstrateRequestException

chain = SubstrateInterface(
	url="wss://kusama-rpc.dwellir.com"
)

print(f"Connected to {chain.name}: {chain.chain} v{chain.version}")

kusama_identity = {}
query = chain.query_map('Identity', 'IdentityOf')
for acc, i in query:
	if i.value[0]['info']['additional']:
		for additional in i.value[0]['info']['additional']:
			if additional[0]['Raw'].lower() == 'github' or additional[0]['Raw'].lower() == 'discord':
				print(acc.value)
				print(i.value[0]['info']['additional'])
	del i.value[0]['deposit'] # should be zero (different)
	del i.value[0]['info']['additional'] # not in new type
	i.value[0]['info']['matrix'] = i.value[0]['info'].pop('riot') # renamed to matrix
	kusama_identity[acc.value] = i.value

kusama_subs = {}
query = chain.query_map('Identity', 'SubsOf')
for acc, i in query:
	zero_deposit_value = (0, i.value[1])
	kusama_subs[acc.value] = zero_deposit_value

kusama_super = {}
super_query = chain.query_map('Identity', 'SuperOf')
for acc, i in super_query:
	kusama_super[acc.value] = i.value

# People

chain = SubstrateInterface(
	url="wss://kusama-people-rpc.polkadot.io"
)

print(f"Connected to {chain.name}: {chain.chain} v{chain.version}")

people_identity = {}
query = chain.query_map('Identity', 'IdentityOf')
for acc, i in query:
	assert(i.value[0]['deposit'] == 0) # should be zero
	del i.value[0]['deposit']
	del i.value[0]['info']['github'] # not in old
	del i.value[0]['info']['discord'] # not in old
	people_identity[acc.value] = i.value

people_subs = {}
query = chain.query_map('Identity', 'SubsOf')
for acc, i in query:
	people_subs[acc.value] = i.value

people_super = {}
super_query = chain.query_map('Identity', 'SuperOf')
for acc, i in super_query:
	people_super[acc.value] = i.value

# Sort and compare

kusama_super = dict(sorted(kusama_super.items()))
people_super = dict(sorted(people_super.items()))

with open("kusama_super.json", "w") as f:
	json.dump(kusama_super, f)
with open("people_super.json", "w") as f:
	json.dump(people_super, f)
print("Wrote Kusama and People SuperOf to files.")

if kusama_super == people_super:
	print('✅ SuperOf')
else:
	print('❌ SuperOf')

kusama_subs = dict(sorted(kusama_subs.items()))
people_subs = dict(sorted(people_subs.items()))

with open("kusama_subs.json", "w") as f:
	json.dump(kusama_subs, f)
with open("people_subs.json", "w") as f:
	json.dump(people_subs, f)
print("Wrote Kusama and People SubsOf to files.")

if kusama_super == people_super:
	print('✅ SubsOf')
else:
	print('❌ SubsOf')

kusama_identity = dict(sorted(kusama_identity.items()))
people = dict(sorted(people_identity.items()))

with open("kusama_identity.json", "w") as f:
	json.dump(kusama_identity, f)
with open("people_identity.json", "w") as f:
	json.dump(people_identity, f)
print("Wrote Kusama and People IdentityOf to files.")

if kusama_identity == people_identity:
	print('✅ IdentityOf')
else:
	print('❌ IdentityOf')
