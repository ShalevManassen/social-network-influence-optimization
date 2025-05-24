import csv
import random
import networkx as nx
import pandas as pd
import numpy as np
import os
from Praducci_simulation import *


# Set value in list if idx is not yet exists
def set_value(list, index, value):
    if index >= len(list):
        list.extend([0] * (index + 1 - len(list)))
    list[index] = value

# Calculating average neighbors per node in costs
def average_neighbors_in_costs_nodes(graph, costs):
    if graph is None or costs is None:
        print("Graph or costs data is missing.")
        return None

    total_neighbors = 0
    count = 0

    for node in costs:
        if node in graph:
            total_neighbors += len(list(graph.neighbors(node)))
            count += 1

    if count == 0:
        print("No matching nodes found in graph.")
        return 0

    average = total_neighbors / count
    print(f"Average number of neighbors per node in costs: {average:.2f}")
    return average


# Returning only the nodes from costs that the number of their neighbors is bigger than average
def filter_high_degree_nodes(graph, costs, average):
    if graph is None or costs is None:
        print("Graph or costs data is missing.")
        return []

    high_degree_nodes = []
    for node in costs:
        if node in graph and len(list(graph.neighbors(node))) >= average:
            high_degree_nodes.append(node)

    print(f"Found {len(high_degree_nodes)} nodes with degree ≥ {average:.2f}")
    return high_degree_nodes



# Given 2 vertex calculating the probability of u to infect v
def find_P_u_v(graph, haters,P_BASE,u,v):
    P_u_v = P_BASE
    friends = graph.neighbors(v)
    for friend in friends:
        if friend in haters:
            P_u_v = P_u_v*(1 - haters[friend])
    return P_u_v


# Creating a list that contains for each influencer the average of his influence on his direct neighbors
def find_average_influence(graph, haters, costs,P_BASE):
    list_average_influence = []
    for user_id in costs:
        friends = list(graph.neighbors(user_id))
        sum_friends_influence = 0
        for friend in friends:
            sum_friends_influence += find_P_u_v(graph, haters,P_BASE,user_id,friend)
        set_value(list_average_influence, user_id, sum_friends_influence/len(friends))
    return list_average_influence

# Returns the indexes of the top `size` influencers with the highest average influence.'''
def find_top_group(size, list_average_influence):
    influence_array = np.array(list_average_influence)
    top_k_indices = influence_array.argsort()[-size:][::-1]
    return top_k_indices.tolist()

# Computing "spreadness" per of specific group
def compute_spreadness(graph, group):
    group = [node for node in group if node in graph]
    n = len(group)
    if n < 2:
        return 0.0

    total_length = 0
    count = 0

    for i in range(n):
        for j in range(i + 1, n):
            u = group[i]
            v = group[j]
            if nx.has_path(graph, u, v):
                try:
                    path_len = nx.shortest_path_length(graph, source=u, target=v)
                    total_length += path_len
                    count += 1
                except nx.NetworkXError:
                    continue

    if count == 0:
        return float('inf')

    return total_length / count


# Finding "num_samples" of sub groups from initial_group that their (sum costs) = budget
def sampled_possible_groups(initial_group, costs, budget, num_samples):

    valid_samples = set()
    attempts = 0
    max_attempts = num_samples * 100  # Limit total attempts to avoid infinite loops

    while len(valid_samples) < num_samples and attempts < max_attempts:
        attempts += 1
        random.shuffle(initial_group)
        group = []
        total = 0
        for node in initial_group:
            cost = costs[node]
            if total + cost <= budget:
                group.append(node)
                total += cost
            if total == budget:
                valid_samples.add(tuple(sorted(group)))
                break
    print('found {} valid samples'.format(len(valid_samples)))
    return [list(sample) for sample in valid_samples]


# Given a list of valid groups returning the k groups with highest spreadness
def top_spreadness(valid_groups, graph, compute_spreadness, k):
    print ('starting top spreadness computation')
    scored = [(group, compute_spreadness(graph, group)) for group in valid_groups]
    scored.sort(key=lambda x: x[1], reverse=True)
    print ('finished top spreadness computation')
    return [group for group, score in scored[:k]]

def top_sum_influence(list_groups, influence_per_node, t):
    # Calculate sum of influence for each group
    group_influence_sums = []
    for group in list_groups:
        group_sum = sum(influence_per_node[node] for node in group if node in influence_per_node)
        group_influence_sums.append((group, group_sum))

    # Sort groups by sum of influence in descending order
    group_influence_sums.sort(key=lambda x: x[1], reverse=True)

    # Return the top t groups
    return [group for group, _ in group_influence_sums[:t]]


def average_num_tests_simulates(graph, group, haters, p_base, rounds, num_tests):
    total = 0
    for i in range(num_tests):
        total += simulate_influence(graph, group, haters, p_base, rounds)
    return total / num_tests


def greedy_based_simulate(possible_groups, graph, haters, p_base, rounds,num_tests):
    print ('starting greedy based simulation')
    S_0 = possible_groups[0]
    average_max = average_num_tests_simulates(graph, possible_groups[0], haters, p_base, rounds,num_tests)
    for group in possible_groups:
        average = average_num_tests_simulates(graph, group, haters, P_BASE, ROUNDS, num_tests)
        print(group, average)
        if average_max < average:
            S_0 = group
            average_max = average
    return S_0



if __name__ == '__main__':
    BUDGET = 1500
    ROUNDS = 6
    P_BASE = 0.2
    EXAMPLE_INFLUENCERS_FILENAME = '123456789_987654321.csv'
    FRIENDSHIPS_FILENAME = 'NoseBook_friendships.csv'
    HATERS_FILENAME = 'haters.csv'
    COSTS_FILENAME = 'costs.csv'

    print('--- Praducci Influence Simulation ---')

    # 1. Load data
    print('\nLoading data files...')
    graph = read_graph(filename=FRIENDSHIPS_FILENAME)
    haters = read_haters(filename=HATERS_FILENAME)
    costs = read_costs(filename=COSTS_FILENAME)

    average = average_neighbors_in_costs_nodes(graph, costs)

    nodes_above_average = filter_high_degree_nodes(graph, costs, average)

    influence_per_node = find_average_influence(graph, haters, nodes_above_average, P_BASE)

    initial_group = find_top_group(700,influence_per_node)

    valid_groups = sampled_possible_groups(initial_group, costs, BUDGET, num_samples = 3000)

    top_spreadness_groups = top_spreadness(valid_groups, graph, compute_spreadness, k = 200)

    top_sum_influence_groups =  top_sum_influence (top_spreadness_groups,influence_per_node,t = 100)

    S_0 = greedy_based_simulate(top_sum_influence_groups,graph, haters, P_BASE, ROUNDS ,num_tests = 1000)

    print ('chosen:' , S_0, average_num_tests_simulates(graph, S_0, haters, P_BASE, ROUNDS, num_tests = 1000))

    submit_influencers(S_0, '212746499', '316352244', costs, haters, filename=None)






