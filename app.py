from dash import Dash, html, dcc, Input, Output, State, ctx, no_update, dash_table
import sys
import pickle
import pandas as pd
from src.plot_graph import plot_subgraph,collapse_names

graph_file = sys.argv[1]
node_df = None
edge_df = None

with open(graph_file, "rb") as outfile:
	node_df = pickle.load(outfile)
	edge_df = pickle.load(outfile)

num_subgraphs = 0 if len(node_df) == 0 else int(node_df["subgraph"].max() + 1)

app = Dash(__name__)


app.layout = html.Div([
	dcc.Store(id='graph-data'),

	html.Div(children=[
				
				html.Div(children=[

						dcc.Graph(
							figure = plot_subgraph(node_df[node_df["subgraph"] == 0], edge_df[edge_df["subgraph"] == 0]), 
							id = 'fig',
							style = {
								"max-height": "80vh",
								"aspect-ratio": "1/1"

							}),

						html.Div(children=[
								html.Div(
									children=html.Button("<<<", id="subgraph-prev"), 
									style={"flex": 1, "border": "1px solid black"}
								),
								html.Div(children=[
										"Group ",
										html.Span(min(1, num_subgraphs), id="subgraph-index"),
										" / ",
										html.Span(str(num_subgraphs), id="subgraph-maxindex")
									],
									style={"flex": 1, "border": "1px solid black"}
								),
								html.Div(
									children=html.Button(">>>", id="subgraph-next"), 
									style={"flex": 1, "border": "1px solid black"}
								),
							],
							style = {
								"width": "90%",
								"display": "flex",
								"margin-left": "auto",
								"margin-right": "auto",
								"text-align": "center"
							}
						),

						html.Div(
							children="", 
							id="clicked_node", 
							style={
								"whiteSpace": "pre-wrap",
								"max-height": "100px",
								"min-height": "25px",
								"overflow-y": "scroll",
								"padding": "5px",
								"padding-left": "10px",
								"background": "beige",
								"border": "1px solid black",
								"margin-top": "10px"
							}
						)
					],
					style = {
						"flex": 1,
						"height": "100%",
						"padding": "15px",
						"position": "sticky",
						"top": "0px"
					}
				),
				
				html.Div(children=[
						html.H3("Neighbor information"),
						dash_table.DataTable(
							data = None, 
							columns = [{"name": i, "id": i} for i in ["Name", "Node weight", "Edge weight"]],
							id = 'edge_table',
							fixed_rows = { "headers": True },
							style_cell = {
								"whiteSpace": "pre-line",
								"textAlign": "right",
								"verticalAlign": "top"
							},
							style_cell_conditional = [
								{
									"if": { "column_id": "Name" },
									"textAlign": "left"
								}
							],
							style_table = {
								"width": "90%",
								"margin": "auto",
								"height": "100%"
							}
						)
					], 
					style={
						"flex": 1,
						"text-align": "center"
					}
				)
		],
		style = {
			"display": "flex",
			"width": "100%"
		}
	)
])

def get_point_index (point_data):
	if point_data is not None and 'points' in point_data and len(point_data['points']) == 1:
		return point_data['points'][0]['pointIndex']
	return -1

# graph-data
#	{
#		"subgraph_index": #,
#		"current": { "point_index": #, "node_id": # }
#		"neighbors": [
#			{ "point_index": #, "node_id": #, "edge_id": # },
#			{ "point_index": #, "node_id": #, "edge_id": # }
#		]
#	}

@app.callback(
	Output('graph-data', 'data'),
	Output('edge_table', 'active_cell'),
	Input('subgraph-index', 'children'),
	Input('fig', 'clickData'),
	Input('fig', 'hoverData'),
	Input('edge_table', 'active_cell')
)
def update_graph_data (subgraph_index, click_data, hover_data, active_cell):

	active_cell_out = None
	trigger = ""
	triggered = list(ctx.triggered_prop_ids.keys())
	if len(triggered) > 0:
		trigger = triggered[0]

	subgraph_index = int(subgraph_index) - 1
	data = {}
	data["subgraph_index"] = subgraph_index
	data["trigger"] = ""
 
	# If the subgraph is changed, return data
	if trigger == "subgraph-index.children":
		data["trigger"] = trigger
		return data,active_cell_out

	else:

		# Get subset of nodes and edges
		node_subdf = node_df[node_df['subgraph'].eq(subgraph_index)]
		edge_subdf = edge_df[edge_df['subgraph'].eq(subgraph_index)]

		click_index = get_point_index(click_data)
		hover_index = get_point_index(hover_data)

		# If a row of the table is clicked, simulate click
		if trigger == "edge_table.active_cell":
			click_index = -1
			hover_index = -1
			for i,node_id in enumerate(node_subdf["node"]):
				if active_cell["row_id"] == node_id:
					click_index = i
					break

		# If there is click data, compute the clicked nodes and its neighbors
		if click_index > -1:

			# Find the corresponding node by row number
			clicked_node = node_subdf.iloc[click_index, :]
			clicked_node_id = clicked_node["node"]

			data["current"] = {
				"point_index": click_index,
				"node_id": clicked_node_id
			}

			data["neighbors"] = []

			neighbor_is_hovered = False

			# Get connected edges for clicked node
			adj_edges = edge_subdf[(edge_subdf['source'].eq(clicked_node_id)) | (edge_subdf['target'].eq(clicked_node_id))]

			# For each edge, get the neighboring node and edge information
			records = []
			for edge_id,edge in adj_edges.iterrows():

				# Find the neighboring node based on the clicked node
				adj_node_id = edge["source"]
				if edge["source"] == clicked_node_id:
					adj_node_id = edge["target"]

				# Iterate through nodes by row
				#    Note that the node row does not necessarily equal the node index

				for node_row,node_id in enumerate(node_subdf["node"]):
					if adj_node_id == node_id:

						data["neighbors"].append({
							"point_index": node_row,
							"edge_id": edge_id,
							"node_id": node_id
						})

						# Check if the hovered node is part of the neighbors
						if node_row == hover_index:
							neighbor_is_hovered = True

			# For click/active cell triggers, return data
			if trigger != "fig.hoverData":
				data["trigger"] = trigger
				return data,active_cell_out
			
			# For hover triggers, only update data if a neighboring node is hovered
			elif hover_index > -1 and neighbor_is_hovered:
				data["trigger"] = trigger
				data["hover"] = {
					"point_index": hover_index,
					"node_id": node_subdf["node"].iloc[hover_index]
				}
				return data,active_cell_out

	return no_update,no_update

@app.callback(
	Output('fig', 'figure'),
	Input('graph-data', 'data'),
	State('fig', 'figure')
)
def update_figure (graph_data, figure):
	subgraph_index = graph_data["subgraph_index"]
	node_subdf = node_df[node_df["subgraph"] == subgraph_index]
	edge_subdf = edge_df[edge_df["subgraph"] == subgraph_index]

	# If subgraph-index changes, make new plot
	if graph_data["trigger"] == "subgraph-index.children":
		return plot_subgraph(node_subdf, edge_subdf)

	# If there is a change in click, just update graph components instead of generating new graph
	elif (graph_data["trigger"] == "fig.clickData" or graph_data["trigger"] == "fig.hoverData" or graph_data["trigger"] == "edge_table.active_cell") and "current" in graph_data:

		click_index = graph_data["current"]["point_index"]

		figure['data'][-1]['marker']['color'] = len(node_subdf) * ["white"]
		figure['data'][-1]['marker']['color'][click_index] = "yellow"

		if "neighbors" in graph_data:
			for neighbor in graph_data["neighbors"]:
				figure['data'][-1]['marker']['color'][neighbor['point_index']] = "red"

		if "hover" in graph_data:
			figure['data'][-1]['marker']['color'][graph_data["hover"]['point_index']] = "pink"

		if click_index > -1:
			return figure
		
	return no_update


@app.callback(
	Output('edge_table', 'data'),
	Output('edge_table', 'selected_cells'),
	Input('graph-data', 'data')
)
def update_edge_table (graph_data):
	subgraph_index = graph_data["subgraph_index"]
	records = []
	selected_cells = []
 
	if "current" in graph_data:

		# Get subset of nodes and edges
		node_subdf = node_df[node_df['subgraph'].eq(subgraph_index)]
		edge_subdf = edge_df[edge_df['subgraph'].eq(subgraph_index)]

		# Iterate through neighbors

		for neighbor_row,neighbor in enumerate(graph_data["neighbors"]):
			edge_id = neighbor["edge_id"]
			node_id = neighbor["node_id"]
			node_row = neighbor["point_index"]

			edge = edge_subdf.loc[edge_id]
			node = node_subdf.iloc[node_row,:]

			records.append({
				"id": node_id,
				"Name": collapse_names(node["name"], sep="\n"), 
				"Node weight": "{:10.3f}".format(node["weight"]),
				"Edge weight": "{:10.3f}".format(edge["weight"])
			})

		records = sorted(records, key = lambda x: x["Edge weight"], reverse=True) 

		# Move hovered node row to top of the table
		if "hover" in graph_data:
			for i,record in enumerate(records):
				if graph_data["hover"]["node_id"] == record["id"]:
					records.insert(0, records.pop(i))
					selected_cells = [ { "row": 0, "column": i } for i in range(3) ]
					break

	return records, selected_cells


@app.callback(
	Output('clicked_node', 'children'),
	Input('graph-data', 'data')
)
def update_clicked_node_info (graph_data):
	subgraph_index = graph_data["subgraph_index"]
	if "current" in graph_data:
		clicked_node = node_df[(node_df["subgraph"] == subgraph_index) & (node_df["node"].eq(graph_data["current"]["node_id"]))].iloc[0]
		return collapse_names(clicked_node["name"], sep="\n")
	return ""


@app.callback(
	Output('subgraph-index', 'children'),
	Output('fig', 'clickData'),
	Output('fig', 'hoverData'),
	Input('subgraph-prev', 'n_clicks'),
	Input('subgraph-next', 'n_clicks'),
	State('subgraph-index', 'children'),
	State('subgraph-maxindex', 'children')
)
def choose_subgraph(subgraph_prev, subgraph_next, subgraph_index, subgraph_maxindex):
	subgraph_index = int(subgraph_index)
	subgraph_maxindex = int(subgraph_maxindex)
	if "subgraph-prev" == ctx.triggered_id and subgraph_index > 1:
		return subgraph_index - 1, None, None
	elif "subgraph-next" == ctx.triggered_id and subgraph_index < subgraph_maxindex:
		return subgraph_index + 1, None, None
	return no_update, no_update, no_update


if __name__ == '__main__':
	app.run_server(debug=False)
	pass
