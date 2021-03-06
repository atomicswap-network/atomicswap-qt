# Copyright (c) 2015-2020 The Decred developers
# Copyright (c) 2019-2020 The atomicswap-qt developers
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from .address import b58_address_to_hash160, hash160_to_b58_address, hash160
from .coind import Coind
from .contract import (estimate_redeem_serialize_size, fee_for_serialize_size, create_sig,
                       is_dust_output, verify, redeem_p2sh_contract, calc_fee_per_kb)
from .transaction import atomic_swap_extract, deserialize, deserialize_witness, MsgTx, OutPoint, TxIn, TxOut
from .script import extract_pkccript_addrs, ScriptType, pay_to_addr_script, unparse_script
from .util import to_amount, amount_format

import binascii

from typing import Tuple


class RedeemError(Exception):
    pass


def redeem(contract_str: str, contract_tx_str: str, secret_str: str, coind: Coind) -> Tuple[MsgTx, int]:
    contract = binascii.a2b_hex(contract_str)
    secret = binascii.a2b_hex(secret_str)
    try:
        contract_tx = deserialize_witness(contract_tx_str, coind)
    except Exception:
        contract_tx = deserialize(contract_tx_str, coind)
    pushes = atomic_swap_extract(contract)
    recipient_addr = hash160_to_b58_address(pushes["recipient_addr_hash"], coind.p2pkh)
    contract_hash160 = hash160(contract)
    contract_out = -1
    for i, tx_out in enumerate(contract_tx.tx_outs):
        sc, addr = extract_pkccript_addrs(tx_out.pkscript, coind)
        if sc != ScriptType.ScriptHash:
            continue
        _, addr_hash = b58_address_to_hash160(addr, coind)
        if addr_hash == contract_hash160:
            contract_out = i
            break
    if contract_out == -1:
        raise RedeemError("Transaction does not contain the contract output!")
    addr = coind.getrawchangeaddress()
    out_script = pay_to_addr_script(addr, coind)
    contract_txhash = contract_tx.get_txid()[::-1]
    contract_outpoint = OutPoint(contract_txhash, contract_out)
    fee_per_kb, min_fee_per_kb = coind.get_fee_per_byte()
    tx_in = TxIn(contract_outpoint, b"", [], 0xffffffff)
    tx_out = TxOut(0, unparse_script(out_script))
    if coind.ver_id:
        expiry_height = coind.getblockcount() + 20
    else:
        expiry_height = 0
    redeem_tx = MsgTx(coind, tx_in, tx_out, pushes["locktime"], expiry_height)
    redeem_size = estimate_redeem_serialize_size(contract, redeem_tx.tx_outs)
    fee = fee_for_serialize_size(fee_per_kb, redeem_size)
    value = contract_tx.tx_outs[contract_out].value - fee
    tx_out.change_params(value=value)
    if is_dust_output(tx_out, min_fee_per_kb):
        raise RedeemError("redeem output value of {} is dust".format(value))
    redeem_tx.change_params(tx_out=tx_out)
    redeem_sig, redeem_pubkey = create_sig(redeem_tx, 0, contract, recipient_addr, coind)
    redeem_sig_script = unparse_script(redeem_p2sh_contract(contract, redeem_sig, redeem_pubkey, secret))
    tx_in.change_params(sig_script=redeem_sig_script)
    redeem_tx.change_params(tx_in=tx_in)
    print(redeem_print(redeem_tx, fee, coind))
    if verify:
        pass
    return redeem_tx, fee


def redeem_print(redeem_tx: MsgTx, fee: int, coind: Coind) -> str:
    redeem_txhash = redeem_tx.get_txid()
    redeem_fee_per_kb = amount_format(calc_fee_per_kb(fee, redeem_tx.serialize_witness_size()), coind.decimals)
    result = ("Redeem fee: " + str(to_amount(fee, coind.decimals)) + " " +
              coind.unit + " ({}/KB)".format(redeem_fee_per_kb, coind.unit) + "\n" +
              "Redeem transaction ({}):".format(redeem_txhash.hex()) + "\n" +
              redeem_tx.serialize_witness().hex())
    return result
