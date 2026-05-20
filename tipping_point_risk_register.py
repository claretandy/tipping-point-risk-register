import pandas as pd
import numpy as np
import itertools
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, GeoJSONDataSource, TapTool, BoxSelectTool, LassoSelectTool
from bokeh.layouts import column, row
from bokeh.io import curdoc
from bokeh.models import Select
from bokeh.transform import factor_cmap
import matplotlib.pyplot as plt
from bokeh.palettes import Category10, Category20
from bokeh.models import LabelSet
from bokeh.models import CDSView, BooleanFilter
from bokeh.models.glyphs import Segment
import regionmask
import json


def create_bokeh_dummy_df():
    np.random.seed(42)
    impact_sectors = [
        "Food Security", "Water Security", "Health", "Energy and Infrastructure", "Coastal and Marine", "Ecosystems"
    ]
    ipcc_regions = [
        'GIC', 'NWN', 'NEN', 'WNA', 'CNA', 'ENA', 'NCA', 'SCA', 'CAR', 'NWS', 'NSA', 'NES', 'SAM',
        'SWS', 'SES', 'SSA', 'NEU', 'WCE', 'EEU', 'MED', 'SAH', 'WAF', 'CAF', 'NEAF', 'SEAF', 'WSAF',
        'ESAF', 'MDG', 'RAR', 'WSB', 'ESB', 'RFE', 'WCA', 'ECA', 'TIB', 'EAS', 'ARP', 'SAS', 'SEA',
        'NAU', 'CAU', 'EAU', 'SAU', 'NZ', 'EAN', 'WAN'
    ]
    tipping_elements = [
        "Amazon", "AMOC", "Greenland Ice Sheet", "West Antarctic Ice Sheet"
    ]
    timescales = ["Years", "Decades", "Centuries"]
    confidence_levels = ["Very Low", "Low", "Medium", "High"]
    conf_weights = [0.85, 0.10, 0.05, 0.0]
    combos = list(itertools.product(impact_sectors, ipcc_regions, tipping_elements))
    df = pd.DataFrame(combos, columns=["Impact Sector", "IPCC Region", "Tipping Element"])
    n_rows = len(df)
    df["Impact Severity"] = np.random.uniform(0, 1, n_rows)
    df["Impact Severity Error"] = np.random.uniform(0.02, 0.1, n_rows)
    df["Global Warming Level"] = np.random.uniform(1.5, 6.5, n_rows)
    df["Global Warming Level Error"] = np.random.uniform(0.05, 0.2, n_rows)
    df["Tipping Point Likelihood"] = np.random.uniform(0, 1, n_rows)
    df["Tipping Point Likelihood Error"] = np.random.uniform(0.02, 0.1, n_rows)
    df["Tipping Point Confidence"] = np.random.choice(confidence_levels, n_rows, p=conf_weights)
    df["Impact Confidence"] = np.random.choice(confidence_levels, n_rows, p=conf_weights)
    df["Timescale"] = np.random.choice(timescales, n_rows)
    df["Impact Severity Upper"] = df["Impact Severity"] + df["Impact Severity Error"]
    df["Impact Severity Lower"] = df["Impact Severity"] - df["Impact Severity Error"]
    df["Global Warming Level Upper"] = df["Global Warming Level"] + df["Global Warming Level Error"]
    df["Global Warming Level Lower"] = df["Global Warming Level"] - df["Global Warming Level Error"]

    return df

def load_geodata():

    # 1a. Get AR6 land regions
    ar6_land = regionmask.defined_regions.ar6.land
    # 1b. Using the regionmask package, get countries at 1:110m resolution
    countries_lowres = regionmask.defined_regions.natural_earth_v5_0_0.countries_110

    # 2a. Convert to GeoDataFrame
    ar6_gdf = ar6_land.to_geodataframe()
    # 2b. Convert world to GeoDataFrame
    world_gdf = countries_lowres.to_geodataframe()

    # 3a. Convert to GeoJSON string
    ar6_geojson = GeoJSONDataSource(geojson=ar6_gdf.to_json())
    world_geojson = GeoJSONDataSource(geojson=world_gdf.to_json())

    # Get the IPCC regions lookup table
    # Build the lookup dictionary from feature properties
    ar6_json = json.loads(ar6_geojson.geojson)
    ipcc_region_lookup = {
        feature['properties']['abbrevs']: feature['properties']['names']
        for feature in ar6_json['features']
    }

    return ar6_geojson, world_geojson, ipcc_region_lookup


def get_palette(n_colors):

    if n_colors <= 10:
        palette = Category10[n_colors]
    elif n_colors <= 20:
        palette = Category20[n_colors]
    else:
        # Option 2: Generate with matplotlib for more colors
        palette = [plt.cm.tab20(i / n_colors) for i in range(n_colors)]
        # Convert RGBA to hex
        palette = ['#%02x%02x%02x' % (int(r * 255), int(g * 255), int(b * 255)) for r, g, b, _ in palette]

    return palette

# Prepare GeoJSON data of IPCC regions and country boundaries
ar6, world, ipcc_region_lookup = load_geodata()

df = create_bokeh_dummy_df()
initial_region = df["IPCC Region"].unique()[0]
initial_tipping = df["Tipping Element"].unique()[0]
initial_impact = df["Impact Sector"].unique()[0]
initial_compare = "IPCC Region" # "Impact Sector"
compare_factors = list(df[initial_compare].unique())

# Get a palette with enough colors for the unique values in the initial_compare category
# Step 1: Get unique values
unique_values = df[initial_compare].unique()
n_colors = len(unique_values)
# Step 2: Get palette
palette = get_palette(n_colors)
color_map = dict(zip(compare_factors, palette))

# Use full names in dropdown
region_options = [ipcc_region_lookup[code] for code in df["IPCC Region"].unique()]
initial_region_full = ipcc_region_lookup[initial_region]
region_select = Select(title="IPCC Region", value=initial_region_full, options=region_options)
tipping_select = Select(title="Tipping Element", value=initial_tipping, options=list(df["Tipping Element"].unique()))
impact_select = Select(title="Impact Sector", value=initial_impact, options=list(df["Impact Sector"].unique()))
compare_options = ["Impact Sector", "Tipping Element", "IPCC Region"]
compare_select = Select(title="Compare by", value=initial_compare, options=compare_options)
df["color"] = df[compare_select.value].map(color_map)

# Map compare categories to their Select widgets
compare_to_widget = {
    "IPCC Region": region_select,
    "Tipping Element": tipping_select,
    "Impact Sector": impact_select,
}

# Disable the Select corresponding to the current compare_by
for key, widget in compare_to_widget.items():
    widget.disabled = (key == initial_compare)

# def get_filtered_source(region, tipping, impact):
#     compare_var = compare_select.value
#     filters = []
#     # Map full name back to code for filtering
#     region_code = {v: k for k, v in ipcc_region_lookup.items()}.get(region, region)
#     if compare_var != "IPCC Region":
#         filters.append(df["IPCC Region"] == region_code)
#     if compare_var != "Tipping Element":
#         filters.append(df["Tipping Element"] == tipping)
#     if compare_var != "Impact Sector":
#         filters.append(df["Impact Sector"] == impact)
#     if filters:
#         filtered = df[np.logical_and.reduce(filters)]
#     else:
#         filtered = df.copy()
#
#     return ColumnDataSource(filtered)

def get_filtered_source(region, tipping, impact):
    compare_var = compare_select.value
    # Map full name back to code for filtering
    region_code = {v: k for k, v in ipcc_region_lookup.items()}.get(region, region)
    mask = np.ones(len(df), dtype=bool)
    if compare_var != "IPCC Region":
        mask &= (df["IPCC Region"] == region_code)
    if compare_var != "Tipping Element":
        mask &= (df["Tipping Element"] == tipping)
    if compare_var != "Impact Sector":
        mask &= (df["Impact Sector"] == impact)
    data = df.copy()
    data["visible"] = mask
    print(data["visible"].value_counts())
    return ColumnDataSource(data)

source = get_filtered_source(initial_region, initial_tipping, initial_impact)

# Map figure of IPCC regions with selection capability

# Create map figure
map_fig = figure(width=700, title="IPCC AR6 Regions")
map_fig.axis.visible = False
map_fig.grid.visible = False
# Add country boundaries for context, fill with a light grey and thin lines
r_world = map_fig.patches(
    'xs', 'ys',
    source=world,
    fill_color='lightgrey',
    line_color='white',
    line_width=0.5
)
# Add IPCC AR6 regions on top, which are selectable
r_ar6 = map_fig.patches(
    'xs', 'ys',
    source=ar6,
    fill_color='color',
    line_color='black',
    line_width=1
)

# Add TapTool for selection
map_fig.add_tools(TapTool(renderers=[r_ar6]))

# Callback to update when a region is selected
def map_select_callback(attr, old, new):
    # selected_index = ar6.selected['id']['indices']
    selected_index = ar6.selected.indices[0] if ar6.selected.indices else None

    if selected_index:
        parsed_json = json.loads(ar6.geojson)
        features = parsed_json['features']
        # Get the selected feature
        selected_feature = features[selected_index]
        # Extract the region_code property
        selected_region_code = selected_feature['properties']['abbrevs']
        region_select.value = ipcc_region_lookup[selected_region_code]

        # Highlight the point on the scatterplot if comparing by IPCC Region
        if compare_select.value == "IPCC Region":
            # Find the index in the source where "IPCC Region" matches
            indices = [
                i for i, code in enumerate(source.data["IPCC Region"])
                if code == selected_region_code
            ]
            source.selected.indices = indices
        else:
            source.selected.indices = []
    else:
        source.selected.indices = []
        region_select.value = initial_region_full

ar6.selected.on_change('indices', map_select_callback)

# Scatter plot figure ...
p = figure(
    title="Global Warming Level vs Impact Severity",
    x_axis_label="Impact Severity",
    y_axis_label="Global Warming Level",
    width=800,
    height=600,
    x_range=(0, 1),
    y_range=(1.5, 6.5)
)

# Scatter plot colored by Impact Sector with legend
scatter = p.scatter(
    x="Impact Severity",
    y="Global Warming Level",
    source=source,
    size=8,
    color=factor_cmap(compare_select.value, palette=palette, factors=compare_factors),
    # legend_field=compare_select.value,
    alpha=0.7,
    selection_alpha=1.0,  # fully opaque when selected
    nonselection_alpha=0.2,  # more transparent when not selected
    view=CDSView(filter=BooleanFilter(source.data["visible"]))
)

# Add x error bars (horizontal segments)
p.segment(
    x0="Impact Severity Lower", x1="Impact Severity Upper",
    y0="Global Warming Level", y1="Global Warming Level",
    source=source, color="color", line_width=1,
    view=CDSView(filter=BooleanFilter(source.data["visible"]))
)

# Add y error bars (vertical segments)
p.segment(
    x0="Impact Severity", x1="Impact Severity",
    y0="Global Warming Level Lower", y1="Global Warming Level Upper",
    source=source, color="color", line_width=1,
    view=CDSView(filter=BooleanFilter(source.data["visible"]))
)

# Filter the source data for visible points
visible_mask = np.array(source.data["visible"])
labels_source = ColumnDataSource({k: np.array(v)[visible_mask] for k, v in source.data.items()})

# Initial label set
labels = LabelSet(
    x="Impact Severity",
    y="Global Warming Level",
    text=compare_select.value,
    source=labels_source,
    text_font_size="8pt",
    text_align="left",
    x_offset=5,
    y_offset=5,
    # view=CDSView(filter=BooleanFilter(source.data["visible"]))  # Not available for LabelSet
)
p.add_layout(labels)

# Add selection tools to the scatterplot
p.add_tools(BoxSelectTool())
p.add_tools(LassoSelectTool())
p.toolbar.active_drag = p.select_one(BoxSelectTool)

def update(attr, old, new):
    global scatter, labels
    # Save current selection
    selected_indices = list(source.selected.indices)
    group_by = compare_select.value
    # Disable the Select corresponding to the current compare_by
    for key, widget in compare_to_widget.items():
        widget.disabled = (key == group_by)
    # Get unique factors from the filtered data
    filtered_df = df.copy()
    compare_var = compare_select.value
    region_code = {v: k for k, v in ipcc_region_lookup.items()}.get(region_select.value, region_select.value)
    if compare_var != "IPCC Region":
        filtered_df = filtered_df[filtered_df["IPCC Region"] == region_code]
    if compare_var != "Tipping Element":
        filtered_df = filtered_df[filtered_df["Tipping Element"] == tipping_select.value]
    if compare_var != "Impact Sector":
        filtered_df = filtered_df[filtered_df["Impact Sector"] == impact_select.value]
    factors = list(filtered_df[group_by].unique())
    pal = get_palette(len(factors))
    color_map = dict(zip(factors, pal))

    new_source = get_filtered_source(region_select.value, tipping_select.value, impact_select.value)
    source.data = dict(new_source.data)
    source.data["color"] = [color_map.get(val, "#000000") for val in source.data[group_by]]

    # Restore selection (only if indices are still valid)
    if selected_indices:
        max_index = len(source.data["Impact Severity"]) - 1
        valid_indices = [i for i in selected_indices if i <= max_index]
        source.selected.indices = valid_indices

    # Remove old scatter
    p.renderers = [r for r in p.renderers if r != scatter]
    # Remove old error bars (Segment glyphs)
    p.renderers = [r for r in p.renderers if not (hasattr(r, "glyph") and isinstance(r.glyph, Segment))]
    # Remove old labels
    # Find all LabelSet instances in the plot, and remove them
    labelsets = p.select({'type': LabelSet})
    try:
        for label_set in labelsets:
            p.center.remove(label_set)
    except (ValueError, AttributeError):
        pass

    # Add new scatter with updated legend_field and color mapping
    scatter = p.scatter(
        x="Impact Severity",
        y="Global Warming Level",
        source=source,
        size=8,
        color=factor_cmap(group_by, palette=pal, factors=factors),
        alpha=0.7,
        selection_alpha=1.0,  # fully opaque when selected
        nonselection_alpha=0.2,  # more transparent when not selected
        view=CDSView(filter=BooleanFilter(source.data["visible"]))
    )

    # Add x error bars (horizontal segments)
    p.segment(
        x0="Impact Severity Lower", x1="Impact Severity Upper",
        y0="Global Warming Level", y1="Global Warming Level",
        source=source, color="color", line_width=1,
        view=CDSView(filter=BooleanFilter(source.data["visible"]))
    )

    # Add y error bars (vertical segments)
    p.segment(
        x0="Impact Severity", x1="Impact Severity",
        y0="Global Warming Level Lower", y1="Global Warming Level Upper",
        source=source, color="color", line_width=1,
        view=CDSView(filter=BooleanFilter(source.data["visible"]))
    )

    # Filter the source data for visible points
    visible_mask = np.array(source.data["visible"])
    labels_source = ColumnDataSource({k: np.array(v)[visible_mask] for k, v in source.data.items()})
    # Add new labels
    labels = LabelSet(
        x="Impact Severity",
        y="Global Warming Level",
        text=group_by,
        source=labels_source,
        text_font_size="8pt",
        text_align="left",
        x_offset=5,
        y_offset=5
    )
    p.add_layout(labels)

    # Update legend
    # p.legend.title = group_by
    # p.legend.location = "center"
    # p.legend.click_policy = "hide"
    # # Remove previous legend from right (if any)
    # for layout in list(p.right):
    #     p.right.remove(layout)
    # # Add updated legend to the right
    # p.add_layout(p.legend[0], 'right')

def scatter_select_callback(attr, old, new):
    # Get selected indices in scatterplot
    selected_indices = source.selected.indices
    if not selected_indices:
        ar6.selected.indices = []
        return

    # Get selected IPCC Region codes from scatterplot
    selected_codes = set([source.data["IPCC Region"][i] for i in selected_indices])

    # Find indices in ar6 GeoJSON where abbrevs match selected codes
    ar6_json = json.loads(ar6.geojson)
    map_indices = [
        i for i, feature in enumerate(ar6_json["features"])
        if feature["properties"]["abbrevs"] in selected_codes
    ]
    ar6.selected.indices = map_indices

source.selected.on_change("indices", scatter_select_callback)
region_select.on_change("value", update)
tipping_select.on_change("value", update)
impact_select.on_change("value", update)
compare_select.on_change("value", update)

# Remove the default legend
# p.legend.visible = False
# legend = p.legend[0]
# p.add_layout(legend, 'right')
# legend.visible = True
# p.legend.title = compare_select.value
# p.legend.location = "center"  # "top_left"
# p.legend.click_policy = "hide"
# Move legend outside plot area (to the right)
# p.add_layout(p.legend[0], 'right')

# layout = column(row(region_select, tipping_select), p)
# layout = column(row(region_select, tipping_select, impact_select, compare_select), row(map_fig,p))
# Dropdowns in a row above the scatterplot
region_row = row(region_select, align="end")
dropdown_row = row(tipping_select, impact_select, compare_select, align="start")
scatter_col = column(dropdown_row, p)
map_col = column(region_row, map_fig)
# Map and scatterplot side by side
layout = row(map_col, scatter_col)
curdoc().add_root(layout)

# # If running as a script, use: show(layout)
# # Run with bokeh serve --show tipping_point_risk_register.py