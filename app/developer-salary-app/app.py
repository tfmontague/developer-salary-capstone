# Import necessary modules
from shiny import App, ui, render, Inputs  # Import everything directly from shiny
import pandas as pd
import joblib
import numpy as np
from ipyleaflet import Map, Choropleth, Marker, Popup
from ipywidgets.embed import embed_minimal_html
from branca.colormap import linear
from ipywidgets import HTML
import json
import tempfile

# Load data and model
developer_data = pd.read_csv("Transformed_Developer_Survey_Data.csv")
state_salary_data = pd.read_csv("Transformed_bls2023_dl.csv")
best_forest_model = joblib.load("best_forest_model_optimized.pkl")
model_columns = joblib.load("model_columns_optimized.pkl")
scaler = joblib.load("scaler.pkl")
with open("us-states.json") as f:
    geo_json_data = json.load(f)

# Map state names to FIPS codes
state_name_to_fips = {
    "Alabama": "01", "Alaska": "02", "Arizona": "04", "Arkansas": "05", "California": "06",
    "Colorado": "08", "Connecticut": "09", "Delaware": "10", "District of Columbia": "11",
    "Florida": "12", "Georgia": "13", "Hawaii": "15", "Idaho": "16", "Illinois": "17",
    "Indiana": "18", "Iowa": "19", "Kansas": "20", "Kentucky": "21", "Louisiana": "22",
    "Maine": "23", "Maryland": "24", "Massachusetts": "25", "Michigan": "26", "Minnesota": "27",
    "Mississippi": "28", "Missouri": "29", "Montana": "30", "Nebraska": "31", "Nevada": "32",
    "New Hampshire": "33", "New Jersey": "34", "New Mexico": "35", "New York": "36",
    "North Carolina": "37", "North Dakota": "38", "Ohio": "39", "Oklahoma": "40",
    "Oregon": "41", "Pennsylvania": "42", "Rhode Island": "44", "South Carolina": "45",
    "South Dakota": "46", "Tennessee": "47", "Texas": "48", "Utah": "49", "Vermont": "50",
    "Virginia": "51", "Washington": "53", "West Virginia": "54", "Wisconsin": "55",
    "Wyoming": "56", "Puerto Rico": "72"
}
state_salary_data["FIPS"] = state_salary_data["State"].map(state_name_to_fips)
state_salary_dict = state_salary_data.set_index("FIPS")["AvgSalary"].to_dict()

# Helper functions
def to_str_choices(series):
    return sorted(map(str, series.unique()))

# Ensure input data fields are numeric and handle preprocessing for model input
def ensure_numeric(df, columns):
    for col in columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def prepare_input(user_input):
    input_df = pd.DataFrame([user_input])
    input_df = ensure_numeric(input_df, ['YearsCode', 'OrgSize', 'EdLevel', 'WorkExp', 'Industry', 'DevType', 'RemoteWork'])
    input_df = pd.get_dummies(input_df)
    input_df = input_df.reindex(columns=model_columns, fill_value=0)
    scaled_input_df = input_df.copy()
    scaled_input_df[scaler.feature_names_in_] = scaler.transform(input_df[scaler.feature_names_in_])
    return scaled_input_df

# Define the UI layout with custom styling
app_ui = ui.page_fluid(
    # CSS style to control value box height
    ui.tags.style("""
        .value-box {
            height: 200px;  /* Adjust height as desired */
        }
        .grid-map-container {
            height: 300px;  /* Set a fixed height for both the grid and map */
        }
    """),

    ui.layout_sidebar(
        ui.sidebar(
            ui.h3("Developer Salary Estimator Dashboard", width=1),

            ui.input_select("age_range", "Age Range:", choices=to_str_choices(developer_data["Age Range"])),
            ui.input_select("remote_work", "Remote Work:", choices=to_str_choices(developer_data["RemoteWork"])),
            ui.input_select("education_level", "Education Level:", choices=to_str_choices(developer_data["EdLevel"])),
            ui.input_slider("years_code", "Years of Coding Experience:", min=int(developer_data["YearsCode"].min()), max=int(developer_data["YearsCode"].max()), value=5),
            ui.input_select("dev_type", "Developer Type:", choices=to_str_choices(developer_data["DevType"])),
            ui.input_select("org_size", "Organization Size:", choices=to_str_choices(developer_data["OrgSize"])),
            ui.input_slider("work_exp", "Years of Work Experience:", min=int(developer_data["WorkExp"].min()), max=int(developer_data["WorkExp"].max()), value=5),
            ui.input_select("industry", "Industry:", choices=to_str_choices(developer_data["Industry"])),
            ui.input_select("state", "State:", choices=to_str_choices(state_salary_data["State"]))
        ),
        # Main content area with reduced height for value boxes
        ui.layout_column_wrap(
            ui.div(
                ui.value_box("",ui.output_text("estimated_salary")),
                class_="value-box"  # Apply custom class for height control
            ),
            ui.div(
                ui.value_box("", ui.output_text("average_state_salary")),
                class_="value-box"  # Apply custom class for height control
            ),
            width=1/2
        ),
        # Layout for the map and data grid with titles and fixed heights
        ui.layout_column_wrap(
            # Data Grid with title
            ui.div(
                ui.h3("Explore Developer Salary Survey Raw Data"),  # Title for the data grid
                ui.output_data_frame("developer_data_grid"),
                class_="fixed-height-container"
            ),
            # Map with title
            ui.div(
                ui.h3("State Salary Map"),  # Title for the map
                ui.output_ui("state_map"),
                class_="fixed-height-container"
            ),
            width=1/2
        )
    )
)

# Define the server function
def server(input, output, session):

    # Estimated salary calculation
    @output
    @render.text
    def estimated_salary():
        user_input = {
            "Age Range": input.age_range(),
            "RemoteWork": input.remote_work(),
            "EdLevel": input.education_level(),
            "YearsCode": input.years_code(),
            "DevType": input.dev_type(),
            "OrgSize": input.org_size(),
            "WorkExp": input.work_exp(),
            "Industry": input.industry
        }
        input_df = prepare_input(user_input)
        estimated_salary = best_forest_model.predict(input_df)[0]
        return f"Estimated Salary: ${estimated_salary:,.2f}"

    # Average state salary based on selected state
    @output
    @render.text
    def average_state_salary():
        avg_salary = state_salary_data[state_salary_data["State"] == input.state()]["AvgSalary"].values[0]
        return f"Average Salary in {input.state()}: ${avg_salary:,.2f}"
    

    # Data grid output for developer data with dropdown filters for each column
    @output
    @render.data_frame
    def developer_data_grid():
        return render.DataGrid(developer_data, filters=True)
    
    # Render the map with salary data for the selected state
    @output
    @render.ui
    def state_map():
        selected_state = input.state()
        avg_salary = state_salary_data[state_salary_data["State"] == selected_state]["AvgSalary"].values[0]
        colormap = linear.viridis.scale(state_salary_data["AvgSalary"].min(), state_salary_data["AvgSalary"].max())
        m = Map(center=(37.0902, -95.7129), zoom=4, scroll_wheel_zoom=True)
        choro_layer = Choropleth(
            geo_data=geo_json_data,
            choro_data=state_salary_dict,
            colormap=colormap,
            key_on="id",
            style={'fillOpacity': 0.6, 'weight': 0.5},
            border_color='black'
        )
        m.add_layer(choro_layer)
        selected_state_fips = state_name_to_fips[selected_state]
        selected_state_data = next(
            feature for feature in geo_json_data["features"]
            if feature["id"] == selected_state_fips
        )
        coords = selected_state_data["geometry"]["coordinates"][0][0]
        popup_content = HTML(f"<b>{selected_state}</b><br>Avg Salary: ${avg_salary:,.2f}")
        marker = Marker(location=[coords[1], coords[0]])
        popup = Popup(child=popup_content, max_width=200)
        marker.popup = popup
        m.add_layer(marker)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as temp_file:
            temp_file_path = temp_file.name
            embed_minimal_html(temp_file_path, views=[m], title="Topaz Montague's Developer Salary Estimator")
        with open(temp_file_path, "r") as file:
            map_html = file.read()
        return ui.HTML(map_html)

# Create the Shiny app
app = App(app_ui, server)
