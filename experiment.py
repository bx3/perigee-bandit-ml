import sys
import config
from oracle import PeersInfo
from communicator import Note
import networkx as nx
import writefiles
import schedule 
import adversary
from oracle import NetworkOracle 
from selector import Selector
from collections import defaultdict
from schedule import NetworkState
import time
import numpy as np
import comm_network
import random
from optimizer import Optimizer
from bandit import Bandit
import initnetwork
import math
from multiprocessing.pool import Pool
# from concurrent.futures import ThreadPoolExecutor


class Experiment:
    def __init__(self, node_hash, link_delay, node_delay, num_node, in_lim, out_lim, name, sybils, window):
        self.nh = node_hash
        self.ld = link_delay
        self.nd = node_delay
        self.num_node = num_node
        self.nodes = {} # nodes are used for communicating msg in network
        self.conns = {} # key is node, value if number of connection
        self.selectors = {} # selectors for choosing outgoing conn for next time
        self.in_lim = in_lim
        self.out_lim = out_lim
        self.outdir = name

        self.timer = time.time()

        self.adversary = adversary.Adversary(sybils)
        self.snapshots = []

        self.pools = Pool(processes=config.num_thread) 
        # ThreadPoolExecutor(max_workers=config.num_thread)

        self.optimizers = {}
        self.bandits = {}
        self.window = window 

        self.broad_nodes = []

        

    # generate networkx graph instance
    def construct_graph(self):
        G = nx.Graph()
        for i, node in self.nodes.items():
            for u in node.outs:
                delay = self.ld[i][u] + node.node_delay/2 + self.nodes[u].node_delay/2
                assert(i != u)
                G.add_edge(i, u, weight=delay)
        return G

    def update_ins_conns(self):
        all_nodes = list(self.nodes.keys())
        conns_ins = defaultdict(list)
        for i in all_nodes:
            node = self.nodes[i]
            for out in node.outs:
                self.nodes[out].ins.add(i)
                conns_ins[out].append(i)
        return conns_ins

    def update_conns(self, out_conns):
        # correctness check
        num_double_conn = 0

        #for i, peers in out_conns.items():
        for i in range(len(out_conns)):
            peers = out_conns[i]
            for p in peers:
                if i in out_conns[p]:
                    print(i, out_conns[i])
                    print(p, out_conns[p])
                    print('')
                    num_double_conn += 1
        if num_double_conn> 0:
            print("num_double_conn > 0", num_double_conn)

        nodes = self.nodes
        # for i, peers in out_conns.items():
        for i in range(len(out_conns)):
            peers = out_conns[i]
            if len(set(peers)) != len(peers):
                print('Error. Repeat peer')
                print(i, peers)
                sys.exit(1)

            nodes[i].outs = set(peers)
            nodes[i].ins.clear()
            nodes[i].recv_time = 0
            nodes[i].received = False
        conn_ins = self.update_ins_conns()
        return conn_ins

    def get_outs_neighbors(self):
        out_neighbor = np.zeros((self.num_node, self.out_lim))
        for i in range(self.num_node):
            out_neighbor[i] = list(self.nodes[i].outs)
        return out_neighbor

    def init_optimizers(self):
        for i in range(self.num_node):
            self.optimizers[i] = Optimizer(
                i,
                self.num_node,
                self.out_lim,
                self.window,
            )

    def init_bandits(self):
        for i in range(self.num_node):
            self.bandits[i] = Bandit(
                i,
                self.out_lim,
                self.num_node 
            )

    def init_graph(self, outs_neighbors):

        for i in range(self.num_node):
            node_delay = self.nd[i]
            self.nodes[i] = Note(
                i,
                node_delay,
                self.in_lim,
                self.out_lim,
                outs_neighbors[i]
            )
        ins_conns = self.update_ins_conns()
        self.init_selectors(outs_neighbors, ins_conns)
        self.init_optimizers()
        self.init_bandits()

        # for i in range(config.num_node):
            # print(i, outs_neighbors[i], ins_conns[i])
        # sys.exit(1)

    def take_snapshot(self, epoch):
        name =  str(config.network_type)+'_'+str(config.method)+"V1"+"Round"+str(epoch)+".txt"
        outpath = self.outdir + "/" + name
            
        G = self.construct_graph()
        outs_neighbors = self.get_outs_neighbors()

        structure_name =  self.outdir + "/" + 'structure_' +  str(epoch) + '.txt'
        writefiles.write_conn(structure_name, outs_neighbors)

        writefiles.write(outpath, G, self.nd, outs_neighbors, self.num_node)

        curr_time = time.time()
        elapsed = curr_time - self.timer 
        self.timer = curr_time
        print("Finish. Recording", epoch, "since last record using", elapsed)

    def init_selectors(self, out_conns, in_conns):
        for u in range(self.num_node):
            # if smaller then it is adv
            if u in self.adversary.sybils:
                self.selectors[u] = Selector(u, True, out_conns[u], in_conns[u], None)
            else:
                self.selectors[u] = Selector(u, False, out_conns[u], in_conns[u], None)

    def broadcast_msgs(self, num_msg):
        # key is id, value is a dict of peers whose values are lists of relative timestamp
        time_tables = {i:defaultdict(list) for i in range(self.num_node)}
        abs_time_tables = {i:defaultdict(list) for i in range(self.num_node)}
        for _ in range(num_msg):
            broad_node = -1
            if self.nh is None:
                broad_node = np.random.randint(self.num_node)
            else:
                broad_node = comm_network.get_broadcast_node(self.nh)
            self.broad_nodes.append(broad_node)
            comm_network.broadcast_msg(broad_node, self.nodes, self.ld, self.nh, time_tables, abs_time_tables)
        
        return time_tables, abs_time_tables

    def update_selectors(self, outs_conns, ins_conn):
        for i in range(self.num_node):
            self.selectors[i].update(outs_conns[i], ins_conn[i])
            
    def shuffle_nodes(self):
        update_nodes = None
        if not config.sybil_update_priority:
            update_nodes = [i for i in range(self.num_node)]
            random.shuffle(update_nodes)
        else:
            # make sure sybils node knows the information first
            all_nodes = set([i for i in range(self.num_node)])
            honest_nodes = list(all_nodes.difference(set(self.adversary.sybils)))
            random.shuffle(honest_nodes)
            update_nodes = sybils + honest_nodes
        assert(update_nodes != None and len(update_nodes) == self.num_node)
        return update_nodes

    def accumulate_optimizer(self, time_table, abs_time_tables):
        for i in range(self.num_node):
            if config.use_abs_time:
                self.optimizers[i].append_time(abs_time_tables[i])
            else:
                self.optimizers[i].append_time(time_table[i])

    def start(self, max_epoch, record_epochs):
        last = time.time()
        network_state = NetworkState(self.num_node, self.in_lim) 
        for epoch in range(max_epoch):
            print("\t\tepoch", epoch)
            
            oracle = NetworkOracle(config.is_dynamic, self.adversary.sybils, self.selectors)
            last = time.time()
            outs_conns = {} 
            network_state.reset(self.num_node, self.in_lim)
            # alternate optimizing
            if config.use_matrix_completion:
                if epoch-self.window in record_epochs:
                    self.take_snapshot(epoch-self.window)

                time_tables, abs_time_tables = self.broadcast_msgs(1)
                self.accumulate_optimizer(time_tables, abs_time_tables)

                if epoch > self.window:
                    # work on matrix factorization
                    node_order = self.shuffle_nodes()
                    outs_conns = schedule.select_nodes_by_matrix_completion(
                        self.nodes, 
                        self.ld, 
                        self.nh, 
                        self.optimizers,
                        self.bandits,
                        node_order, 
                        time_tables, 
                        abs_time_tables,
                        self.in_lim,
                        self.out_lim, 
                        network_state,
                        self.pools
                        )
                else:
                    # random connections
                    outs_conns = initnetwork.generate_random_outs_conns(
                        self.out_lim, 
                        self.in_lim, 
                        self.num_node)
                    for i in range(self.num_node):
                        if len(outs_conns[i]) != self.out_lim:
                            print(outs_conns[i])
                            sys.exit(1)

                # updates connections
                ins_conn = self.update_conns(outs_conns)
            else:
                if epoch in record_epochs:
                    self.take_snapshot(epoch)
                # 1,2,3 hop selection
                time_tables = self.broadcast_msgs(config.num_msg)
                print("broadcast", round(time.time() - last,2))
                node_order = self.shuffle_nodes()
                outs_conns = schedule.select_nodes(
                    self.nodes, 
                    self.ld, 
                    config.num_msg, 
                    self.nh, 
                    self.selectors,
                    oracle,
                    node_order, 
                    time_tables, 
                    self.in_lim,
                    self.out_lim, 
                    network_state
                    )
                print("select", round(time.time() - last, 2))
                # update outs ins
                ins_conn = self.update_conns(outs_conns)
                # self.check()
                self.update_selectors(outs_conns, ins_conn)

            
            # print(epoch, len(self.selectors[0].seen), sorted(self.selectors[0].seen))

    def check(self):
        for i in range(self.num_node):
            out_conns = self.selectors[i].desc_conn
            num = 0
            for u, v in out_conns:
                if u == i:
                    num += 1
            if num != 3:
                print(i, out_conns)
                sys.exit(1)

    def start_complete_graph(self, max_epoch, record_epochs):
        start = time.time()
        for epoch in range(max_epoch):
            print('epoch', epoch)
            if epoch in record_epochs:
                self.take_snapshot(epoch)
        finish = time.time()
        print(finish - start, 'elapsed')

    # def analytical_complete_graph(self):
        # print('start analytical analyze')
        # name =  str(config.network_type)+'_'+str(config.method)+"V1"+"Round"+'0'+".txt"
        # outpath = self.outdir + "/" + name
        # with open(outpath, 'w') as w:
            # for i in range(self.num_node):
                # for j in range(self.num_node):
                    # if i == j:
                        # delay = 0
                    # else:
                        # delay = self.ld[i][j] + self.nd[j]
                    # w.write(str(delay) + '  ')
                # w.write('\n')






