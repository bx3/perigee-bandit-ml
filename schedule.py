import numpy as np
import sys
import random
import config 
import visualizer
from oracle import PeersInfo
import copy
import comb_subset
from collections import namedtuple
from collections import defaultdict
import math 
import time
import solver

# networkstate and oracle may look redundant, but oracle is used to answering 2hop
# networkstate is essential for checking if connection is possible
class NetworkState:
    def __init__(self, num_node, in_lim):
        self.num_in_conn = {} 
        self.in_conn_lim = {}
        self.conn = defaultdict(list)
        self.num_node = num_node
        for i in range(num_node):
            self.num_in_conn[i] = 0
            self.in_conn_lim[i] = in_lim

    def reset(self, num_node, in_lim):
        self.num_in_conn = {} 
        self.in_conn_lim = {}
        self.conn = defaultdict(list)
        for i in range(num_node):
            self.num_in_conn[i] = 0
            self.in_conn_lim[i] = in_lim

    def is_conn_addable(self, u, v):
        # if someone I want to connect, already connect me
        if u in self.conn[v]:
            #print(u, 'in', v)
            return False
        if v in self.conn[u]:
            #print(v, 'in', u)
            return False

        if self.num_in_conn[v] < self.in_conn_lim[v]:
            return True
        else:
            #print(v, 'in lim', u)
            return False

    def is_conn_keepable(self, u, v):
        # TODO
        if u in self.conn[v]:
            #print(u, 'in', v)
            return False
        if v in self.conn[u]:
            #print(v, 'in', u)
            return False

        if self.num_in_conn[v] < self.in_conn_lim[v]:
            return True
        else:
            #print(v, 'in lim', u)
            return False


    # v is the dst node 
    def add_in_connection(self, u, v):
        self.conn[u].append(v)
        self.num_in_conn[v] += 1

# selected by i
def is_connectable(i, p, network_state, selected):
    if p == i:
        return False 
    if p in selected:
        return False
    if network_state.is_conn_addable(i, p):
        return True
    else:
        return False

def get_pullable_arms(i, network_state):
    valid_arms = []
    for p in range(network_state.num_node):
        if p != i:
            if network_state.is_conn_addable(i, p):
                valid_arms.append(p)
    return valid_arms

def print_bandits(bandits):
    for i, bandit in bandits.items():
        arms = bandit.get_pulled_arms()
        print('\t\t*****', i)
        for a in arms:
            region, node = a
            print('node',i,'region',region,'peer',node, 'scores',bandit.ucb_table[a].score_list)


def bandit_selection(bandit, W, H, X, network_state, outs_neighbors, out_lim):
    bandit.update_times(W, X)

    valid_arms = get_pullable_arms(bandit.id, network_state)

    arms = bandit.pull_arms(valid_arms)
    # for p in arms:
        # if not is_connectable(bandit.id, p, network_state, outs_neighbors[bandit.id]):
            # print('arm not pullable', bandit.id, p)
            # print(outs_neighbors[bandit.id])
            # print(outs_neighbors[p])
            # print(network_state.num_in_conn[p])
            # sys.exit(1)

    pulled_arms = bandit.get_pulled_arms()
    
    # for l in range(out_lim):
        # a = arms[l]
        # if (l, a) in pulled_arms:
            # arm_not_pulled = bandit.get_num_not_pulled()
            # print(bandit.id, 'pull an old arm', l, a)
            # print(arm_not_pulled, '\n')

    return arms

def select_nodes_by_matrix_completion(nodes, ld, nh, optimizers, bandits, update_nodes, time_tables, abs_time_tables, in_lim, out_lim, network_state, pools):
    outs_neighbors = defaultdict(list)
    num_node = len(nodes)

    start = time.time()
    if config.num_thread == 1:
        for i in update_nodes:
            W, H = optimizers[i].matrix_factor()

            X =  optimizers[i].construct_table()
            # argmin_top_peers = choose_best_neighbor(H)
            peers = bandit_selection(bandits[i], W, H, X, network_state, outs_neighbors, out_lim)
            # argmin_peers = get_argmin_peers(i, H, network_state, outs_neighbors, out_lim)

            # debug
            # print(i, argmin_top_peers, argmin_peers)
            # print(get_times(argmin_top_peers, X, out_lim))
            # print(get_times(argmin_peers, X, out_lim))
            # sys.exit(2)

            for p in peers:
                if is_connectable(i, p, network_state, outs_neighbors[i]):
                    outs_neighbors[i].append(p)
                    network_state.add_in_connection(i, p)
        print('selection', round(time.time()-start, 2))
        # print_bandits(bandits)
        # sys.exit(2)
    else:
        multithread_matrix_factor(optimizers, bandits, update_nodes, network_state, outs_neighbors, out_lim, pools)

    # choose random peers
    num_random = 0
    start = time.time()
    for i in update_nodes:
        trial = 0
        while len(outs_neighbors[i]) < out_lim:
            num_random += 1
            w = np.random.randint(num_node)
            while not is_connectable(i, w, network_state, outs_neighbors[i]):
                w = np.random.randint(num_node)
                trial += 1
                if trial == num_node-1:
                    print(i, 'tried too many trial for random peer')
                    break
            outs_neighbors[i].append(w)
            network_state.add_in_connection(i, w)
    print('num_random', num_random)
    return outs_neighbors
            

# nh is node hash
def select_nodes(nodes, ld, num_msg, nh, selectors, oracle, update_nodes, time_tables, in_lim, out_lim, network_state):
    outs_neighbors = {} # output container
    num_invalid_compose = 0
    # direct peers
    num_rand_1hop = 0
    for i in update_nodes:
        keep_candidates = list(nodes[i].outs)
        if config.both_in_and_out:
            keep_candidates += list(nodes[i].ins)       

        composes = comb_subset.get_config(config.num_keep, 
                keep_candidates,
                len(keep_candidates), 
                network_state,
                i)
        num_invalid_compose += math.comb(len(keep_candidates), config.num_keep) - len(composes)
        if len(composes) == 0:
            peers = selectors[i].select_random_peers(nodes, config.num_keep, network_state)
            num_rand_1hop += 1
            # oracle needs to know the connection
            oracle.update_1_hop_peers(i, peers)
            outs_neighbors[i] = peers
        else:
            for compose in composes:
                if len(compose) != len(set(compose)):
                    print(i)
                    print(compose)
                    print(list(nodes[i].outs))
                    print(list(nodes[i].ins))
                    sys.exit(1)

            peers = selectors[i].select_1hops(time_tables[i], composes, num_msg, network_state)
            # oracle needs to know the connection
            oracle.update_1_hop_peers(i, peers)
            outs_neighbors[i] = peers

    num_added_2hop = 0
    num_added_3hop = 0
    num_added_random = 0
    tot_not_seen = 0
    random.shuffle(update_nodes)
    print('shuffle to select 2hops')
    # two hop peers
    for u in update_nodes:
        peers_info = oracle.get_multi_hop_info(u)
        peers, num_not_seen = selectors[u].select_peers(
                config.num_2_hop, nodes, peers_info.two_hops, network_state)
        oracle.update_2_hop_peers(u, peers)
        outs_neighbors[u] += peers
        num_added_2hop += len(peers)

        tot_not_seen += num_not_seen
        
        # add 3hops
        if out_lim - len(outs_neighbors[u]) > config.num_random:
            num_3_hop = out_lim - len(outs_neighbors[u]) - config.num_random
            peers_info = oracle.get_multi_hop_info(u)
            peers, num_not_seen = selectors[u].select_peers(num_3_hop, nodes, peers_info.three_hops, network_state)
            oracle.update_3_hop_peers(u, peers)
            outs_neighbors[u] += peers
            num_added_3hop += len(peers) 
            tot_not_seen += num_not_seen
    
        # add random
        num_random = out_lim - len(outs_neighbors[u]) 
        num_added_random += num_random

        peers = selectors[u].select_random_peers(nodes, num_random, network_state)
        for p in peers:
            if p in outs_neighbors[u]:
                print(p, 'in neigbors', outs_neighbors[u])
                sys.exit(1)
        outs_neighbors[u] += peers

    # debug
    for u in update_nodes:
        if len(set(outs_neighbors[u])) != out_lim:
            print(u, "has less out neighbors")
            print(outs_neighbors[u])
            print(selectors[u].desc_conn)
            sys.exit(1)
    print('num_rand_1hop', num_rand_1hop,'num_invalid_compose', num_invalid_compose )
    # print('Finish. num2hop', num_added_2hop, 'num3hop', num_added_3hop, 'num rand', num_added_random, 'num no seen', tot_not_seen)
    return outs_neighbors

# simplest
def get_argmin_peers(i, H, network_state, outs_neighbors, out_lim):
    regions_order = [j for j in range(out_lim)]
    random.shuffle(regions_order)
    argsorted_peers = np.argsort(H, axis=1)
    arms = []
    for l in regions_order:
        peers = argsorted_peers[l, :]
        # choose one peers from that regions, peers are sorted in increasing time order
        for p in peers:
            if is_connectable(i, p, network_state, arms):
                arms.append(p)
                break
    return arms



def choose_best_neighbor(H):
    return np.argmin(H, axis=1)

def get_times(peers, X, out_lim):
    times = []
    for k in range(out_lim):
        p = peers[k]
        times.append(X[k, p])
    return times 

def multithread_matrix_factor(optimizers, bandits, update_nodes, network_state, outs_neighbors, out_lim, pools):
    args = []
    W_, H_, X_ = {}, {}, {}
    start = time.time()
    for i in range(len(update_nodes)):
        optimizer = optimizers[i] 
        arg = (i, optimizer.table[-optimizer.window:], optimizer.window, optimizer.N, optimizer.L)
        args.append(arg)

    results = pools.starmap(solver.run_pgd_nmf, args)

    assert(len(results) == len(update_nodes))
    for i in range(len(update_nodes)):
        W, H = results[i]
        W_[i] = W
        H_[i] = H

    for i in update_nodes:
        X = optimizers[i].construct_table()
        # if i == 32:
            # print('schedule', X)
        peers = bandit_selection(bandits[i], W_[i], H_[i], X, network_state, outs_neighbors, out_lim)
        for p in peers:
            if is_connectable(i, p, network_state, outs_neighbors[i]):
                outs_neighbors[i].append(p)
                network_state.add_in_connection(i, p)



       
# futures = []
    # for i in update_nodes:
        # future = pools.submit(optimizers[i].matrix_factor(), None)
        # futures.append(future)
    
    # W_, H_, X_ = {}, {}, {}
    # for i in range(len(futures)):
        # W, H, X = futures[i].result()
        # W_[i] = W
        # H_[i] = H
        # X_[i] = X

    # for i in update_nodes:
        # peers = bandit_selection(bandits[i], W_[i], H_[i], X_[i], network_state, outs_neighbors, out_lim)
        # for p in peers:
            # if is_connectable(i, p, network_state, outs_neighbors[i]):
                # outs_neighbors[i].append(p)
                # network_state.add_in_connection(i, p)


# def init_matrix(X, L):
    # A, B = None, None
    # if config.init_nndsvd:
        # A, B = nndsvd.initial_nndsvd(X, L)
    # else:
        # A, S, B = svds(X, L)
        # I = np.sign(A.sum(axis=0)) # 2 * int(A.sum(axis=0) > 0) - 1
        # A = A.dot(np.diag(I))
        # B = np.transpose((B.T).dot(np.diag(S*I)))
    # return A, B