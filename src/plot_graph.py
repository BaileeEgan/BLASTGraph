import numpy as np
import plotly.graph_objects as go

# Collapse long list of names into a condensed list by genus
#   Example:
#      Bacillus (9)             <- Collapse multiple species into same genus
#      Clostridium difficile    <- Keep fewer species in same genus intact
#      Clostridium spp.
#      Escherichia coli

def collapse_names (name_string, sep=","):
	name_list = sorted(name_string.replace("[", "").replace("]", "").split(","))
	groups = {}

	for name in name_list:
		words = name.split(" ")
		if words[0] not in groups:
			groups[words[0]] = []

		groups[words[0]].append(" ".join(words[1:]))


	new_names = []
	for key,group in groups.items():
		if len(group) <= 3:
			for item in group:
				new_names.append(key + " " + item)
		else:
			new_names.append(key + " (%s)" % len(group))

	return sep.join(new_names)




def plot_subgraph (node_subdf, edge_subdf):
	if len(node_subdf) == 0:
		fig = go.Figure(data = [])

	else:

		edge_traces = []

		edge_subdf = edge_subdf.copy()

		bins = np.linspace(edge_subdf['weight'].min(), edge_subdf['weight'].max(), 6)
		edge_subdf['bin'] = np.digitize(edge_subdf['weight'], bins)

		for bin,subset in edge_subdf.groupby('bin'):

			edge_x = []
			edge_y = []

			for i,row in subset.iterrows():
				source = node_subdf[node_subdf["node"] == row["source"]].iloc[0,:]
				target = node_subdf[node_subdf["node"] == row["target"]].iloc[0,:]

				sx = float(source["x"])
				sy = float(source["y"])
				tx = float(target["x"])
				ty = float(target["y"])

				edge_x += [sx, tx, None]
				edge_y += [sy, ty, None]

			if len(edge_x) > 0:
				edge_traces.append(go.Scatter(
					x = edge_x, 
					y = edge_y,
					line = dict(width=0.5 * float(bin) + 0.1, color="black"),
					hoverinfo = "none",
					mode = "lines",
					showlegend = False
				))


		node_x = node_subdf["x"]
		node_text = node_subdf["name"].apply(collapse_names).str.replace(",", "<br />")
		node_y = node_subdf["y"]
		node_weight = node_subdf["weight"] + 5
		node_linewidth = 0.05 * node_subdf["weight"] + 1
		node_color = len(node_subdf) * ["white"]
		node_linecolor = len(node_subdf) * ["black"]


		node_trace = go.Scatter(
			name = "Nodes",
			x = node_x,
			y = node_y,
			text = node_text,
			hovertemplate = "%{text}<extra></extra>",
			mode = "markers",
			marker = dict(
				size = node_weight,
				color = node_color,
				line = dict(color=node_linecolor, width=node_linewidth)
			),
			showlegend = False
		)

		fig = go.Figure(data = edge_traces + [node_trace])


	fig.update_layout(
		plot_bgcolor  = "#f9f9f9",
		xaxis = dict(showgrid=False, zeroline=False, linecolor="black", showline=True, ticks="outside", mirror=True),
		yaxis = dict(showgrid=False, zeroline=False, linecolor="black", showline=True, ticks="outside", mirror=True),
		xaxis2 = dict(showgrid=False, zeroline=False),
		yaxis2 = dict(showgrid=False, zeroline=False)
	)

	return fig