#! /usr/bin/env python

# Copyright (c) 2014 KU Leuven, ESAT-STADIUS
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# 3. Neither name of copyright holders nor the names of its contributors
# may be used to endorse or promote products derived from this software
# without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import itertools
import functools
import multiprocessing
import threading
import copy
import collections


__all__ = ['pmap', 'Future']


def _fun(f, q_in, q_out):
    while True:
        i, x = q_in.get()
        if i is None:
            break
        value = f(*x)
        d = None
        keys = None
        if hasattr(f, 'call_log'):
            k, v = f.call_log.items()[-1]
            d = (tuple(k), v)
            keys = k._fields
        q_out.put((i, value, d, keys))


# http://stackoverflow.com/a/16071616
def pmap(f, *args):
    """Parallel map using multiprocessing.

    :param f: the callable
    :param args: arguments to f, as iterables
    :returns: a list containing the results

    """
    nprocs = multiprocessing.cpu_count()
    q_in = multiprocessing.Queue(1)
    q_out = multiprocessing.Queue()

    proc = [multiprocessing.Process(target=_fun, args=(f, q_in, q_out))
            for _ in range(nprocs)]
    for p in proc:
        p.daemon = True
        p.start()

    sent = [q_in.put((i, x)) for i, x in enumerate(zip(*args))]
    [q_in.put((None, None)) for _ in range(nprocs)]
    res = [q_out.get() for _ in range(len(sent))]
    [p.join() for p in proc]

    # FIXME: strong coupling between pmap and functions.logged
    if hasattr(f, 'call_log'):
        keys = res[0][3]
        if not f.keys:
            f.keys.extend(keys)
        if f.argtuple is None:
            f.argtuple = collections.namedtuple('args', keys)
        for _, _, d, _ in sorted(res):
            k, v = d
            f.call_log[f.argtuple(*k)] = v

    return [x for i, x, _, _ in sorted(res)]


# http://code.activestate.com/recipes/84317-easy-threading-with-futures/
class Future:
    def __init__(self,func,*param):
        # Constructor
        self.__done=0
        self.__result=None
        self.__status='working'

        self.__S=threading.Semaphore(0)

        # Run the actual function in a separate thread
        self.__T=threading.Thread(target=self.Wrapper, args=(func, param))
        self.__T.setName("FutureThread")
        self.__T.daemon=True
        self.__T.start()

    def __repr__(self):
        return '<Future at '+hex(id(self))+':'+self.__status+'>'

    def __call__(self):
        try:
            self.__S.acquire()
            # We deepcopy __result to prevent accidental tampering with it.
            a=copy.deepcopy(self.__result)
        finally:
            self.__S.release()
        return a

    def join(self):
        self.__T.join()

    def Wrapper(self, func, param):
        # Run the actual function, and let us housekeep around it
#        try:
        self.__result=func(*param)
#        except:
#            self.__result="Exception raised within Future"
        self.__status=str(self.__result)
        self.__S.release()


if __name__ == '__main__':
    pass
