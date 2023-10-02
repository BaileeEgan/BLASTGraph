import pandas as pd
import numpy as np
import igraph as ig
import os
import pickle

def blast_to_graph (blast_file, graph_file, node_col="qacc", edge_col="sacc", force=False):

	if not os.path.exists(graph_file) or force:
		print("Creating graph file from blast results...")
	
		node_df,edge_df = _blast_to_graph(blast_file, node_col, edge_col)

		print("Saving graph file")
		with open(graph_file, "wb") as outfile:
			pickle.dump(node_df, outfile)
			pickle.dump(edge_df, outfile)


def _blast_to_graph (file, node_col = "qacc", edge_col = "sacc"):

	print("...Preprocessing BLAST results...")

	# If not, read in data
	blast = pd.read_csv(file, sep="\t", nrows=500)

	# Keep only best hit for each qacc and sacc
	blast = blast.groupby([node_col, edge_col]).agg({"bitscore": "max"})

	# Calculate top bit scores by grouped qseqid
	blast["top_bitscore"] = blast.groupby("qacc")["bitscore"].transform("max")

	# Trim hits by % top bit score
	blast["bitscore_perc"] = blast["bitscore"] / blast["top_bitscore"]
	blast = blast[blast["bitscore_perc"] >= 0.9]


	node_names = np.array(sorted(blast.index.get_level_values(node_col).unique()))
	edge_names = sorted(blast.index.get_level_values(edge_col).unique())

	node_edges = blast.reset_index().groupby(node_col).agg({ edge_col: lambda x: sorted(x.unique()) })

	node_num_edges = np.array(len(node_names) * [0])


	print("...Finding edges...")

	edges_all = pd.DataFrame(None, columns=["node1", "node2", "edge", "weight"])

	# Iterate through each edge set to find common edges between nodes
	for i in range(len(node_names)):

		# Get node and the neighbors that need edges
		node_i = node_names[i]
		neighbors_i = node_edges.loc[node_i, edge_col]

		for j in range(i + 1, len(node_names)):

			# Get node and the neighbors that need edges
			node_j = node_names[j]
			neighbors_j = node_edges.loc[node_j, edge_col]


			# Compare sets of neighbors to find shared nodes to create edges
			shorter = neighbors_i
			longer = neighbors_j
			if len(shorter) < len(longer):
				shorter = neighbors_j
				longer = neighbors_i


			# Iterate through the shorter to find shared nodes
			for edge_name in shorter:
				if edge_name in longer:

					weight_i = blast.loc[(node_i,edge_name), "bitscore_perc"]
					weight_j = blast.loc[(node_j,edge_name), "bitscore_perc"]

					weight_avg = 0.5 * (weight_i + weight_j)

					edges_all.loc[len(edges_all)] = [node_i, node_j, edge_name, weight_avg]
					node_num_edges[i] += 1
					node_num_edges[j] += 1

	# Remove nodes with no edges
	node_names = list(node_names[node_num_edges > 0])

	# Combine edges between the same nodes
	edges_merged = edges_all.groupby(["node1", "node2"], as_index=False).agg({"weight": "sum"})

	# Rename nodes by node index
	edges_merged["node1"] = [node_names.index(n) for n in edges_merged["node1"]]
	edges_merged["node2"] = [node_names.index(n) for n in edges_merged["node2"]]

	# Create graph from edge and node data


	graph = ig.Graph()
	graph.add_vertices(len(node_names))
	graph.add_edges([(n1,n2) for n1,n2 in zip(edges_merged["node1"], edges_merged["node2"])])

	num_vertices = len(graph.vs)

	graph.vs["name"] = node_names
	graph.vs["weight"] = num_vertices * [1]

	graph.es["weight"] = edges_merged["weight"]

	node_df = pd.DataFrame(None, columns=["name", "weight", "subgraph", "x", "y", "community", "node"])
	edge_df = pd.DataFrame(None, columns=["source", "target", "weight", "subgraph", "community"])

	components = graph.connected_components(mode='weak')

	print("...Processing subgraphs...")

	for subgraph_index, component in enumerate(components):

		subgraph = graph.subgraph(component)
		num_vertices = len(subgraph.vs)

		subgraph.vs["subgraph"] = int(subgraph_index)
		subgraph.es["subgraph"] = int(subgraph_index)

		layout = subgraph.layout("kamada_kawai")
		subgraph.vs["x"] = [n[0] for n in layout]
		subgraph.vs["y"] = [n[1] for n in layout]

		for community_index,community in enumerate(subgraph.community_fastgreedy().as_clustering()):
			subgraph.vs[community]["community"] = int(community_index)
			subgraph.es.select(_within=community)["community"] = int(community_index)

		# Group nodes by identical neighbors
		node_groups = {}
		num_vertices = len(subgraph.vs)
		membership = [i for i in range(num_vertices)]

		for node in subgraph.vs.indices:

			neighbors = subgraph.neighbors(node)

			# Insert the current node into the neighbor set
			if node > neighbors[-1]:
				neighbors.append(node)
			else:
				for i,neighbor in enumerate(neighbors):
					if node < neighbor:
						neighbors.insert(i, node)
						break

			# Add node's group into group map
			#   Can only combine nodes with equivalent neighbors and communities
			group_name = str(subgraph.vs[node]["community"]) + "|" + ",".join(map(str, neighbors))

			if group_name not in node_groups:
				node_groups[group_name] = []
			node_groups[group_name].append(node)

		# For each group, set new membership as the lowest index in the group
		for key,group in node_groups.items():
			min_idx = min(group)
			for i in group:
				membership[i] = min_idx

		# Collapse nodes based on identical neighbors
		subgraph.contract_vertices(membership, combine_attrs = {
			"x": "mean", 
			"y": "mean", 
			"weight": "sum", 
			"community": "first", 
			"subgraph": "first", 
			"name": lambda x: ",".join(sorted(x))
		})

		# Combine edges
		subgraph.simplify(combine_edges={
			"weight": sum, 
			"subgraph": "first", 
			"community": "first"
		})

		subgraph.vs["node"] = subgraph.vs.indices

		# Remove empty nodes
		#verts_to_delete = [n for n in range(len(subgraph.vs)) if subgraph.vs["name"][n] == "" ]
		#subgraph.delete_vertices(verts_to_delete)

		# Create dataframes for nodes and edges
		subgraph_node_df = pd.DataFrame({attr: subgraph.vs[attr] for attr in subgraph.vertex_attributes()})
		subgraph_node_df.index.name = "node"

		subgraph_edge_df = subgraph.get_edge_dataframe()
		subgraph_edge_df.index.name = "edge"

		# Removes extraneous edges caused by graph processing
		#rows_to_delete = []
		#for i,row in edge_df.iterrows():
		#	source_subgraph = node_df.loc[row["source"], "subgraph"]
		#	target_subgraph = node_df.loc[row["source"], "subgraph"]
		#	edge_subgraph = row["subgraph"]
		#	if not (source_subgraph == target_subgraph and source_subgraph == edge_subgraph):
		#		rows_to_delete.append(i)
		#edge_df.drop(rows_to_delete, inplace=True)


		if len(node_df) == 0:
			node_df = subgraph_node_df
		else:
			node_df = pd.concat([node_df, subgraph_node_df], ignore_index=True)

		if len(edge_df) == 0:
			edge_df = subgraph_edge_df
		else:
			edge_df = pd.concat([edge_df, subgraph_edge_df], ignore_index=True)

	node_df.to_csv("nodes.tsv", sep="\t")
	edge_df.to_csv("edges.tsv", sep="\t")

	return node_df,edge_df

	