import csv
import random
import networkx as nx
import pandas as pd
import numpy as np
import os

random.seed(42)
np.random.seed(42)

BUDGET = 1500
ROUNDS = 6
P_BASE = 0.2
EXAMPLE_INFLUENCERS_FILENAME = '123456789_987654321.csv'
FRIENDSHIPS_FILENAME = 'NoseBook_friendships.csv'
HATERS_FILENAME = 'haters.csv'
COSTS_FILENAME = 'costs.csv'

def read_graph(filename=FRIENDSHIPS_FILENAME):
	'''Reads the friendship graph from a CSV file.

	Args:
		filename (str): The path to the CSV file containing friendships.
						Expected format: 'user,friend' per line.

	Returns:
		nx.Graph: A NetworkX graph object representing the social network.
				Returns None if the file cannot be read.
	'''
	try:
		df = pd.read_csv(filename)
		graph = nx.from_pandas_edgelist(df, source='user', target='friend')
		print(f'Successfully read graph from {filename}')
		return graph
	except FileNotFoundError:
		print(f'Error: File not found - {filename}')
		return None
	except Exception as e:
		print(f'Error reading graph from {filename}: {e}')
		return None

def read_haters(filename=HATERS_FILENAME):
	'''Reads hater data from a CSV file.

	Args:
		filename (str): The path to the CSV file containing haters.
						Expected format: 'user_id,weight' per line.

	Returns:
		dict: A dictionary mapping hater user IDs (int) to their weights (float).
			  Returns None if the file cannot be read.
	'''
	haters = {}
	try:
		with open(filename, 'r') as f:
			reader = csv.reader(f)
			header = next(reader)
			for row in reader:
				user_id = int(row[0])
				weight = float(row[1])
				haters[user_id] = weight
		print(f'Successfully read haters from {filename}')
		return haters
	except FileNotFoundError:
		print(f'Error: File not found - {filename}')
		return None
	except Exception as e:
		print(f'Error reading haters from {filename}: {e}')
		return None

def read_costs(filename=COSTS_FILENAME):
	'''Reads influencer costs from a CSV file.

	Args:
		filename (str): The path to the CSV file containing costs.
						Expected format: 'user_id,cost' per line.

	Returns:
		dict: A dictionary mapping user IDs (int) to their costs (float).
			  Returns None if the file cannot be read.
	'''
	costs = {}
	try:
		with open(filename, 'r') as f:
			reader = csv.reader(f)
			header = next(reader) # Skip header row
			for row in reader:
				user_id = int(row[0])
				cost = float(row[1])
				costs[user_id] = cost
		print(f'Successfully read costs from {filename}')
		return costs
	except FileNotFoundError:
		print(f'Error: File not found - {filename}')
		return None
	except Exception as e:
		print(f'Error reading costs from {filename}: {e}')
		return None

def read_influencers_from_csv(filename, costs, haters):
	'''Reads selected influencers from a student's CSV file and validates them.

	Args:
		filename (str): The path to the student's influencer CSV file.
						Expected format: 'user_id' per line (header 'user_id').
		costs (dict): Dictionary mapping user IDs to costs.
		haters (dict): Dictionary mapping hater IDs to weights.

	Returns:
		list: A list of validated influencer user IDs (int).
			  Returns None if validation fails or file cannot be read.
	'''
	selected_influencers = []
	total_cost = 0
	try:
		with open(filename, 'r') as f:
			reader = csv.reader(f)
			header = next(reader)
			if header != ['user_id']:
				print(f'Error: Invalid header in {filename}. Expected ["user_id"], got {header}.')
				return None

			seen_ids = set()
			for i, row in enumerate(reader):
				if len(row) == 1:
					try:
						user_id = int(row[0])
						# Check if user exists in cost data (implies they exist in the graph potentially)
						if user_id not in costs:
							print(f'Error: Influencer {user_id} from {filename} (line {i+2}) not found in cost data.')
							return None
						# Check if user is an hater
						if user_id in haters:
							print(f'Error: Selected influencer {user_id} (line {i+2}) is an hater.')
							return None
						# Check for duplicates within the file
						if user_id in seen_ids:
							print(f'Error: Duplicate influencer ID {user_id} found in {filename} (line {i+2}).')
							return None

						selected_influencers.append(user_id)
						seen_ids.add(user_id)
						total_cost += costs.get(user_id, 0) # Add cost, default to 0 if somehow missing post-check

					except ValueError:
						print(f'Error: Invalid user ID format in {filename} on line {i+2}: {row[0]}.')
						return None
				else:
					print(f'Error: Invalid row format in {filename} on line {i+2}: {row}. Expected single user ID.')
					return None

		# Check budget constraint
		if total_cost > BUDGET:
			print(f'Error: Total cost of selected influencers ({total_cost:.2f}) exceeds budget ({BUDGET}).')
			return None

		print(f'Successfully read and validated influencers from {filename}.')
		print(f'Total influencers: {len(selected_influencers)}, Total cost: {total_cost:.2f}, Budget: {BUDGET}')
		return selected_influencers

	except FileNotFoundError:
		print(f'Error: File not found - {filename}')
		return None
	except Exception as e:
		print(f'Error reading influencers from {filename}: {e}')
		return None

def simulate_influence(graph, initial_influencers, haters, p_base=P_BASE, rounds=ROUNDS):
	'''Simulates the influence spread process based on the IC model with haters.

	Args:
		graph (nx.Graph): The social network graph.
		initial_influencers (list): A list of user IDs selected as initial influencers (at t=0).
		haters (dict): A dictionary mapping hater user IDs (int) to their weights (float).
		p_base (float): The base probability of influence transmission.
		rounds (int): The number of simulation rounds (t=1 to t=rounds).

	Returns:
		int: The total number of influenced users (including initial influencers) after the specified rounds.
	'''
	if graph is None or initial_influencers is None or haters is None:
		print('Error: Cannot simulate with invalid graph, initial_influencers, or haters data.')
		return 0

	# Ensure initial influencers are not haters (validation should also catch this)
	haters_set = set(haters.keys())
	current_initial_set = set(initial_influencers) - haters_set
	influenced_nodes = set(current_initial_set)

	all_nodes_in_graph = list(graph.nodes())

	for _ in range(1, rounds + 1):
		newly_influenced_this_round = set()
		# Iterate through ALL nodes to check if they can become infected *in this round*
		for candidate in all_nodes_in_graph:
			# Check if candidate is already influenced or is an hater
			if candidate in influenced_nodes or candidate in haters_set:
				continue

			try:
				candidate_neighbors = set(graph.neighbors(candidate))
			except nx.NetworkXError:
				continue # Cannot be infected if no neighbors

			# Find neighbors who were influenced *before* this round started AND are not haters
			influencing_neighbors = {
				u for u in candidate_neighbors
				if u in influenced_nodes and u not in haters_set
			}

			# Only proceed if there are neighbors who could potentially influence
			if not influencing_neighbors:
				continue

			# Calculate the combined anti-influence product
			hater_neighbors_of_candidate = {a for a in candidate_neighbors if a in haters_set}
			anti_influence_product = 1.0
			for hater_node in hater_neighbors_of_candidate:
				anti_influence_product *= (1.0 - haters.get(hater_node, 0.0))

			# Calculate the probability of *not* being infected by ANY active neighbor u
			# P(v not infected) = product over u [ P(v not infected by u) ]
			prob_not_infected_by_any = 1.0
			for u in influencing_neighbors:
				p_effective = p_base * anti_influence_product
				prob_not_infected_by_any *= (1.0 - p_effective)
			# --- END CORRECTION ---

			# The probability of being infected is the complement
			prob_infected = 1.0 - prob_not_infected_by_any

			# Stochastic step: determine if the candidate gets infected
			if random.random() < prob_infected:
				newly_influenced_this_round.add(candidate)

		# Add the newly infected nodes to the set for the next round
		influenced_nodes.update(newly_influenced_this_round)

	# Return the total count of influenced nodes at the end
	return len(influenced_nodes)


def submit_influencers(influencer_list, id1, id2, costs, haters, filename=None):
	'''Creates a CSV file for submission after validating the influencer list.

	Args:
		influencer_list (list): The list of selected influencer user IDs.
		id1 (str): The first student ID.
		id2 (str): The second student ID.
		costs (dict): Dictionary mapping user IDs to costs.
		haters (dict): Dictionary mapping hater IDs to weights.
		filename (str, optional): The desired output filename. Defaults to 'ID1_ID2.csv'.

	Returns:
		bool: True if the file was created successfully, False otherwise.
	'''
	if filename is None:
		filename = f'{id1}_{id2}.csv'

	if not isinstance(influencer_list, list):
		print('Error: influencer_list must be a list.')
		return False
	if not isinstance(id1, str) or not id1 or not isinstance(id2, str) or not id2:
		print('Error: Student IDs must be non-empty strings.')
		return False

	total_cost = 0.0
	seen_influencers = set()

	if not influencer_list:
		print('Warning: The provided influencer list is empty.')

	for i, influencer in enumerate(influencer_list):
		line_num = i + 2
		if not isinstance(influencer, int):
			try:
				influencer = int(influencer)
				influencer_list[i] = influencer
			except (ValueError, TypeError):
				print(f'Error: Influencer ID {influencer} (item {i+1} in list) is not an integer or convertible to one.')
				return False

		# Check existence and cost
		cost = costs.get(influencer) # Use get with no default first
		if cost is None:
			print(f'Error: Influencer {influencer} (item {i+1}) not found in cost data.')
			return False
		if not isinstance(cost, (int, float)): # Ensure cost is numeric
			print(f'Error: Invalid cost type ({type(cost)}) for influencer {influencer}.')
			return False

		# Check if hater
		if influencer in haters:
			print(f'Error: Selected influencer {influencer} (item {i+1}) is an hater.')
			return False
		# Check for duplicates within the list
		if influencer in seen_influencers:
			print(f'Error: Duplicate influencer ID found in list: {influencer} (item {i+1}).')
			return False

		seen_influencers.add(influencer)
		total_cost += cost

	# Check budget
	if total_cost > BUDGET:
		print(f'Error: Total cost ({total_cost:.2f}) exceeds budget ({BUDGET}). Cannot create submission file.')
		return False

	try:
		with open(filename, 'w', newline='') as f:
			writer = csv.writer(f)
			writer.writerow(['user_id'])
			influencer_list.sort()
			for influencer in influencer_list:
				writer.writerow([influencer])
		print(f'Successfully created submission file: {filename}')
		print(f'Total influencers: {len(influencer_list)}, Total cost: {total_cost:.2f}')
		return True
	except Exception as e:
		print(f'Error writing submission file {filename}: {e}')
		return False


if __name__ == '__main__':
	print('--- Praducci Influence Simulation ---')

	# 1. Load data
	print('\nLoading data files...')
	graph = read_graph()
	haters = read_haters()
	costs = read_costs()

	if graph is None or haters is None or costs is None:
		print('\nError loading essential data (graph, haters, or costs). Exiting simulation.')
	else:
		print(f'\nReading example influencers from {EXAMPLE_INFLUENCERS_FILENAME}...')
		if not os.path.exists(EXAMPLE_INFLUENCERS_FILENAME):
			print(f'Error: Example influencers file not found: {EXAMPLE_INFLUENCERS_FILENAME}')
			print('Cannot run simulation or create submission file without it.')
			example_influencers = None
		else:
			example_influencers = read_influencers_from_csv(EXAMPLE_INFLUENCERS_FILENAME, costs, haters)
			# You can just specify you influencers in a list if you want.


		if example_influencers is not None:
			print('\nRunning simulation with example influencers...')
			influenced_count = simulate_influence(graph, example_influencers, haters)
			print(f'\n--- Simulation Complete (Example Influencers) ---')
			print(f'Total influenced users after {ROUNDS} rounds: {influenced_count}')

			print('\nAttempting to create a demonstration submission file using example influencers...')
			# Replace with actual student IDs when used
			STUDENT_ID_1 = '987654321' # Example ID (string)
			STUDENT_ID_2 = '123456789' # Example ID (string)
			success = submit_influencers(example_influencers, STUDENT_ID_1, STUDENT_ID_2, costs, haters)
			if success:
				submission_filename = f'{STUDENT_ID_1}_{STUDENT_ID_2}.csv'
				print(f'Demonstration submission file "{submission_filename}" created.')
			else:
				print('Failed to create demonstration submission file.')
		else:
			print('\nCould not run simulation or create submission file because example influencers file '
				  'was not found or failed validation.')

	print('\n--- End of Simulation Script ---')