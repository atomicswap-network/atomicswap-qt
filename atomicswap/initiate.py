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

from .coind import Coind
from .address import sha256d, is_p2pkh
from .contract import secretSize, contract_tuple, calc_fee_per_kb, build_contract, built_tuple
from .util import to_amount, amount_format

import secrets
import time
from datetime import datetime
from typing import Tuple


def initiate(addr: str, amount: int, coind: Coind, custom_secret: bytes = None) -> Tuple[bytes, built_tuple]:
    assert is_p2pkh(addr, coind), "Address isn't P2PKH."
    if custom_secret is None:
        secret = secrets.token_bytes(secretSize)
    else:
        secret = custom_secret
    secret_hash = sha256d(secret)
    locktime = int(time.mktime(datetime.now().timetuple())) + 48 * 60 * 60
    contract = contract_tuple(addr, amount, locktime, secret_hash)
    b = build_contract(contract, coind)
    print(initiate_print(secret, b, coind))
    return secret, b


def initiate_print(secret: bytes, b: built_tuple, coind: Coind) -> str:
    refund_txhash = b.refundTx.get_txid()
    contract_fee_per_kb = amount_format(calc_fee_per_kb(b.contractFee, b.contractTx.serialize_witness_size()),
                                        coind.decimals)
    refund_fee_per_kb = amount_format(calc_fee_per_kb(b.refundFee, b.refundTx.serialize_witness_size()), coind.decimals)
    result = ("Secret: " + secret.hex() + "\n" +
              "Secret Hash: " + sha256d(secret).hex() + "\n" +
              "Contract Fee: " + str(to_amount(b.contractFee, coind.decimals)) + " " +
              coind.unit + " ({} {}/KB)".format(contract_fee_per_kb, coind.unit) + "\n" +
              "Refund Fee: " + str(to_amount(b.refundFee, coind.decimals)) + " " +
              coind.unit + " ({} {}/KB)".format(refund_fee_per_kb, coind.unit) + "\n" +
              "Contract ({}): ".format(b.contractP2SH) + "\n" +
              b.contract.hex() + "\n" +
              "Contract Transaction ({}): ".format(b.contractTxHash.hex()) + "\n" +
              b.contractTx.serialize_witness().hex() + "\n" +
              "Refund Transaction ({}): ".format(refund_txhash.hex()) + "\n" +
              b.refundTx.serialize_witness().hex())
    return result
