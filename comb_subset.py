import sys
import itertools

# choose 6 out of 8
def get_configs_ind_6():
    return [[0,0,1,1,1,1,1,1],[0,1,0,1,1,1,1,1],[0,1,1,0,1,1,1,1],[0,1,1,1,0,1,1,1],[0,1,1,1,1,0,1,1],[0,1,1,1,1,1,0,1],[0,1,1,1,1,1,1,0],[1,0,0,1,1,1,1,1],[1,0,1,0,1,1,1,1],[1,0,1,1,0,1,1,1],[1,0,1,1,1,0,1,1],[1,0,1,1,1,1,0,1],[1,0,1,1,1,1,1,0],[1,1,0,0,1,1,1,1],[1,1,0,1,0,1,1,1],[1,1,0,1,1,0,1,1],[1,1,0,1,1,1,0,1],[1,1,0,1,1,1,1,0],[1,1,1,0,0,1,1,1],[1,1,1,0,1,0,1,1],[1,1,1,0,1,1,0,1],[1,1,1,0,1,1,1,0],[1,1,1,1,0,0,1,1],[1,1,1,1,0,1,0,1],[1,1,1,1,0,1,1,0],[1,1,1,1,1,0,0,1],[1,1,1,1,1,0,1,0],[1,1,1,1,1,1,0,0]]

def get_configs(configs_ind, node):
    composes = []
    neighbors = list(node.outs)
    for config_ind in configs_ind:
        compose = []
        for i, v in enumerate(config_ind):
            if v == 1:
                compose.append(neighbors[i])
        composes.append(compose)
    return composes

def get_configs_7(neighbors, num_out):
    composes = []
    for i in range(num_out):
        for j in range(i+1, num_out):
            for k in range(j+1, num_out):
                for w in range(k+1, num_out):
                    for r in range(w+1, num_out):
                        for t in range(r+1, num_out):
                            for o in range(t+1, num_out):
                                compose = [neighbors[i], neighbors[j], neighbors[k], neighbors[w], neighbors[r], neighbors[t], neighbors[o]]
                                composes.append(compose)
    return composes 

def get_configs_8(neighbors, num_out):
    composes = []
    for i in range(num_out):
        for j in range(i+1, num_out):
            for k in range(j+1, num_out):
                for w in range(k+1, num_out):
                    for r in range(w+1, num_out):
                        for t in range(r+1, num_out):
                            for o in range(t+1, num_out):
                                for p in range(o+1, num_out):
                                    compose = [neighbors[i], neighbors[j], neighbors[k], neighbors[w], neighbors[r], neighbors[t], neighbors[o], neighbors[p]]
                                    composes.append(compose)
    return composes 

def get_configs_6(neighbors, num_out):
    composes = []
    for i in range(num_out):
        for j in range(i+1, num_out):
            for k in range(j+1, num_out):
                for w in range(k+1, num_out):
                    for r in range(w+1, num_out):
                        for t in range(r+1, num_out):
                            compose = [neighbors[i], neighbors[j], neighbors[k], neighbors[w], neighbors[r], neighbors[t]]
                            composes.append(compose)
    return composes 

def get_configs_5(neighbors, num_out):
    composes = []
    for i in range(num_out):
        for j in range(i+1, num_out):
            for k in range(j+1, num_out):
                for w in range(k+1, num_out):
                    for r in range(w+1, num_out):
                        compose = [neighbors[i], neighbors[j], neighbors[k], neighbors[w], neighbors[r]]
                        composes.append(compose)
    return composes 
def get_configs_4(neighbors, num_out):
    composes = []
    for i in range(num_out):
        for j in range(i+1, num_out):
            for k in range(j+1, num_out):
                for w in range(k+1, num_out):
                    compose = [neighbors[i], neighbors[j], neighbors[k], neighbors[w]]
                    composes.append(compose)
    return composes

# input is a list of neighbor
def get_configs_3(neighbors, num_out, network_state, u):
    composes = []
    for i in range(num_out):
        if network_state.is_conn_addable(u, neighbors[i]):

            for j in range(i+1, num_out):
                if  network_state.is_conn_addable(u, neighbors[j]):

                    for k in range(j+1, num_out):
                        if  network_state.is_conn_addable(u, neighbors[k]):
                            compose = [neighbors[i], neighbors[j], neighbors[k]]
                            composes.append(compose)
    return composes

def get_configs_2(neighbors, num_out):
    composes = []
    for i in range(num_out):
        for j in range(i+1, num_out):
            compose = [neighbors[i], neighbors[j]]
        composes.append(compose)
    return composes 

def get_configs_1(neighbors, num_out):
    composes = []
    for i in range(num_out):
        compose = [neighbors[i]]
        composes.append(compose)
    return composes




def get_configs(neighbors, num_out, network_state, u, num_keep):
    valid_peers = []
    for peer in neighbors:
        if network_state.is_conn_addable(u, peer):
            valid_peers.append(peer)
    valid_peers = sorted(valid_peers)
    composes = []

    for subset in itertools.combinations(valid_peers, num_keep):
        composes.append(subset)
    return composes

def get_config(num_keep, curr_peers, num_out, network_state, u):
    # assert(len(set(curr_peers)) == len(curr_peers))
    composes = get_configs(curr_peers, num_out, network_state, u, num_keep)
    # if num_keep == 3:
        # composes = get_configs_3(curr_peers, num_out, network_state, u)
    # elif num_keep == 2: 
        # composes = get_configs_2(curr_peers, num_out, network_state, u)
    # elif num_keep == 1: 
        # composes = get_configs_1(curr_peers, num_out, network_state, u)
    # elif num_keep == 4: 
        # composes = get_configs_4(curr_peers, num_out, network_state, u)
    # elif num_keep == 5: 
        # composes = get_configs_5(curr_peers, num_out, network_state, u)
    # elif num_keep == 6: 
        # composes = get_configs_6(curr_peers, num_out, network_state, u)
    # elif num_keep == 7: 
        # composes = get_configs_7(curr_peers, num_out, network_state, u)
    # elif num_keep == 8: 
        # composes = get_configs_8(curr_peers, num_out, network_state, u)
    # else:
        # print('Error. choose a valid configs setting')
        # sys.exit(1)
    return composes
