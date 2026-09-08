
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math


# ---------------------------------------------------------
# PAGE SETUP
# ---------------------------------------------------------

st.set_page_config(
    page_title="Southern Region Fuel Delivery Planner",
    page_icon="🚛",
    layout="wide"
)


# ---------------------------------------------------------
# TITLE
# ---------------------------------------------------------

st.title("🚛 Southern Region Fuel Delivery Planner")

st.write(
    "Plan efficient fuel deliveries across service stations "
    "in the Southern Region."
)


# ---------------------------------------------------------
# LOAD STATION DATA
# ---------------------------------------------------------

stations = pd.read_csv("Stations - Sheet1.csv")


# ---------------------------------------------------------
# CLEAN COLUMN NAMES
# ---------------------------------------------------------

stations.columns = (
    stations.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)


# ---------------------------------------------------------
# FIND IMPORTANT COLUMNS
# ---------------------------------------------------------

def find_column(possible_names):

    for name in possible_names:
        if name in stations.columns:
            return name

    return None


name_col = find_column([
    "site_name",
    "station_name",
    "station",
    "site",
    "name"
])

# Your CSV uses:
# x = latitude
# y = longitude
lat_col = "x"
lon_col = "y"

demand_col = find_column([
    "demand",
    "fuel_demand",
    "demand_litres",
    "demand_liters",
    "volume",
    "litres",
    "liters"
])


# ---------------------------------------------------------
# CHECK THAT COORDINATES EXIST
# ---------------------------------------------------------

if lat_col is None or lon_col is None:

    st.error(
        "I could not identify your latitude and longitude columns."
    )

    st.write("Columns found in your CSV:")

    st.write(list(stations.columns))

    st.stop()


# ---------------------------------------------------------
# CREATE STANDARD COLUMNS
# ---------------------------------------------------------

if name_col is not None:

    stations["station_name"] = stations[name_col].astype(str)

else:

    stations["station_name"] = (
        "Station " + stations.index.astype(str)
    )


stations["latitude"] = pd.to_numeric(
    stations[lat_col],
    errors="coerce"
)

stations["longitude"] = pd.to_numeric(
    stations[lon_col],
    errors="coerce"
)


# ---------------------------------------------------------
# FUEL DEMAND
# ---------------------------------------------------------

if demand_col is not None:

    stations["fuel_demand"] = pd.to_numeric(
        stations[demand_col],
        errors="coerce"
    ).fillna(0)

else:

    stations["fuel_demand"] = 0


# ---------------------------------------------------------
# REMOVE BAD COORDINATES
# ---------------------------------------------------------

stations = stations.dropna(
    subset=["latitude", "longitude"]
).copy()


# ---------------------------------------------------------
# HAVERSINE DISTANCE FUNCTION
# ---------------------------------------------------------

def haversine(lat1, lon1, lat2, lon2):

    R = 6371.0

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return R * c


# ---------------------------------------------------------
# DISTANCE BETWEEN TWO STATIONS
# ---------------------------------------------------------

def station_distance(station_a, station_b):

    return haversine(
        station_a["latitude"],
        station_a["longitude"],
        station_b["latitude"],
        station_b["longitude"]
    )


# ---------------------------------------------------------
# SIDEBAR - PLANNING CONTROLS
# ---------------------------------------------------------

st.sidebar.header("🚛 Planning Controls")

number_of_tankers = st.sidebar.number_input(
    "Number of Tankers",
    min_value=1,
    max_value=20,
    value=5,
    step=1
)

tanker_capacity = st.sidebar.number_input(
    "Tanker Capacity (litres)",
    min_value=1000,
    max_value=100000,
    value=30000,
    step=1000
)

max_stops = st.sidebar.number_input(
    "Maximum Stations per Tanker",
    min_value=1,
    max_value=3,
    value=3,
    step=1
)


# ---------------------------------------------------------
# OVERVIEW
# ---------------------------------------------------------

st.subheader("Overview")

total_stations = len(stations)

total_demand = stations["fuel_demand"].sum()

col1, col2, col3, col4 = st.columns(4)

with col1:

    st.metric(
        "Service Stations",
        total_stations
    )

with col2:

    st.metric(
        "Available Tankers",
        number_of_tankers
    )

with col3:

    st.metric(
        "Maximum Stops",
        max_stops
    )

with col4:

    st.metric(
        "Total Fuel Demand",
        f"{total_demand:,.0f} L"
    )


# ---------------------------------------------------------
# STATION DATA
# ---------------------------------------------------------

st.subheader("📍 Service Stations")

st.dataframe(
    stations[
        [
            "station_name",
            "latitude",
            "longitude",
            "fuel_demand"
        ]
    ],
    use_container_width=True
)


# ---------------------------------------------------------
# STATION MAP
# ---------------------------------------------------------

st.subheader("🗺️ Service Station Map")

fig = go.Figure()

fig.add_trace(
    go.Scattermap(
        lat=stations["latitude"],
        lon=stations["longitude"],
        mode="markers",
        marker=dict(
            size=11
        ),
        text=stations["station_name"],
        customdata=stations["fuel_demand"],
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Latitude: %{lat}<br>"
            "Longitude: %{lon}<br>"
            "Demand: %{customdata:,.0f} L"
            "<extra></extra>"
        )
    )
)

fig.update_layout(

    map=dict(
        style="open-street-map",
        center=dict(
            lat=stations["latitude"].mean(),
            lon=stations["longitude"].mean()
        ),
        zoom=7
    ),

    height=600,

    margin=dict(
        l=0,
        r=0,
        t=0,
        b=0
    )
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# ---------------------------------------------------------
# ROUTE GENERATION
# ---------------------------------------------------------

def create_routes(data, tanker_count, maximum_stops):

    data = data.copy()

    data["assigned"] = False

    routes = []

    for tanker_number in range(
        1,
        tanker_count + 1
    ):

        remaining = data[
            data["assigned"] == False
        ]

        if len(remaining) == 0:
            break

        first_index = remaining.index[0]

        route = [
            first_index
        ]

        data.loc[
            first_index,
            "assigned"
        ] = True

        while len(route) < maximum_stops:

            current_index = route[-1]

            remaining = data[
                data["assigned"] == False
            ]

            if len(remaining) == 0:
                break

            current_station = data.loc[
                current_index
            ]

            distances = []

            for index, station in remaining.iterrows():

                distance = station_distance(
                    current_station,
                    station
                )

                distances.append(
                    (index, distance)
                )

            distances.sort(
                key=lambda x: x[1]
            )

            nearest_index = distances[0][0]

            route.append(
                nearest_index
            )

            data.loc[
                nearest_index,
                "assigned"
            ] = True

        routes.append(route)

    return routes, data


# ---------------------------------------------------------
# GENERATE DELIVERY PLAN
# ---------------------------------------------------------

if st.button(
    "🚛 Generate Delivery Plan",
    use_container_width=True
):

    routes, planned_stations = create_routes(
        stations,
        number_of_tankers,
        max_stops
    )

    st.session_state["routes"] = routes
    st.session_state["planned_stations"] = planned_stations


# ---------------------------------------------------------
# DISPLAY DELIVERY PLAN
# ---------------------------------------------------------

if "routes" in st.session_state:

    routes = st.session_state["routes"]

    planned_stations = st.session_state[
        "planned_stations"
    ]

    st.subheader("📋 Delivery Plan")

    route_rows = []

    for tanker_number, route in enumerate(
        routes,
        start=1
    ):

        route_names = []

        route_demand = 0

        route_distance = 0

        for position, index in enumerate(route):

            station = stations.loc[index]

            route_names.append(
                station["station_name"]
            )

            route_demand += station[
                "fuel_demand"
            ]

            if position > 0:

                previous_station = stations.loc[
                    route[position - 1]
                ]

                route_distance += station_distance(
                    previous_station,
                    station
                )

        route_rows.append({

            "Tanker":
                f"Tanker {tanker_number}",

            "Stations":
                " → ".join(route_names),

            "Number of Stops":
                len(route),

            "Fuel Demand (L)":
                round(route_demand, 0),

            "Distance (km)":
                round(route_distance, 2)

        })

    route_table = pd.DataFrame(
        route_rows
    )

    st.dataframe(
        route_table,
        use_container_width=True
    )


# ---------------------------------------------------------
# ROUTE MAP
# ---------------------------------------------------------

if "routes" in st.session_state:

    st.subheader("🚛 Planned Tanker Routes")

    route_fig = go.Figure()

    for tanker_number, route in enumerate(
        st.session_state["routes"],
        start=1
    ):

        route_data = stations.loc[
            route
        ]

        route_fig.add_trace(

            go.Scattermap(

                lat=route_data[
                    "latitude"
                ],

                lon=route_data[
                    "longitude"
                ],

                mode="lines+markers",

                name=f"Tanker {tanker_number}",

                marker=dict(
                    size=10
                ),

                text=route_data[
                    "station_name"
                ],

                hovertemplate=(
                    "<b>%{text}</b>"
                    "<extra></extra>"
                )

            )

        )

    route_fig.update_layout(

        map=dict(

            style="open-street-map",

            center=dict(

                lat=stations[
                    "latitude"
                ].mean(),

                lon=stations[
                    "longitude"
                ].mean()

            ),

            zoom=7

        ),

        height=650,

        margin=dict(
            l=0,
            r=0,
            t=0,
            b=0
        )

    )

    st.plotly_chart(
        route_fig,
        use_container_width=True
    )


# ---------------------------------------------------------
# UNASSIGNED STATIONS
# ---------------------------------------------------------

if "planned_stations" in st.session_state:

    planned_stations = st.session_state[
        "planned_stations"
    ]

    unassigned = planned_stations[
        planned_stations["assigned"] == False
    ]

    st.subheader("⚠️ Unassigned Stations")

    if len(unassigned) == 0:

        st.success(
            "All stations have been assigned to a tanker."
        )

    else:

        st.warning(
            f"{len(unassigned)} station(s) "
            "could not be assigned."
        )

        st.dataframe(
            unassigned[
                [
                    "station_name",
                    "latitude",
                    "longitude",
                    "fuel_demand"
                ]
            ],
            use_container_width=True
        )