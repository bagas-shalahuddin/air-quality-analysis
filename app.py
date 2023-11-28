import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.colors as pc

# Load and preprocess the data
air_quality_data = pd.read_csv('data/combined_air_quality_data.csv')
air_quality_data['timestamp'] = pd.to_datetime(air_quality_data['timestamp'])

# Define the pollutant and weather parameters from the dataset
air_pollutants = air_quality_data.columns[:6].tolist()
weather_factors = air_quality_data.columns[6:10].tolist() + [air_quality_data.columns[11]]

# Custom order for air quality categories
aq_categories = [
    "Good", "Moderate", "Unhealthy for Sensitive Groups", 
    "Unhealthy", "Very Unhealthy", "Hazardous"
]

# Set page config with favicon and title
st.set_page_config(page_title='Air Quality Dashboard', page_icon='https://i.ibb.co/gmPh93j/Pngtree-chemical-plant-air-pollution-5929941.png')

# App title and sidebar configurations
st.title('Air Quality Analysis Dashboard (2013 - 2017) for Beijing Stations')
with st.sidebar:
    st.markdown(
        f"""
        <div style="text-align: center;">
            <img src="https://i.ibb.co/gmPh93j/Pngtree-chemical-plant-air-pollution-5929941.png" alt="logo" width="200">
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.header('Filters')
    station_choices = ['All Stations'] + air_quality_data['station'].unique().tolist()
    selected_stations = st.multiselect('Select Stations', station_choices, default='All Stations')

    aq_category_choices = ['All Categories'] + air_quality_data['Category'].unique().tolist()
    selected_aq_category = st.selectbox('Select AQ Category', aq_category_choices)

    # Date and hour filters
    start_date = st.date_input('Start Date', air_quality_data['timestamp'].min().date())
    end_date = st.date_input('End Date', air_quality_data['timestamp'].max().date())
    start_hour = st.slider('Start Hour', 0, 23, 0)
    end_hour = st.slider('End Hour', 0, 23, 23)

# Filter the dataset based on user selections
if 'All Stations' in selected_stations:
    selected_stations = station_choices[1:]  # Exclude 'All Stations' from the filter

filtered_data = air_quality_data[
    (air_quality_data['station'].isin(selected_stations)) &
    (air_quality_data['Category'].isin([selected_aq_category] if selected_aq_category != 'All Categories' else aq_category_choices)) &
    (air_quality_data['timestamp'].dt.date.between(start_date, end_date)) &
    (air_quality_data['timestamp'].dt.hour.between(start_hour, end_hour))
]

# Main app layout with tabs
tab1, tab2, tab3, tab4 = st.tabs(["Key Metrics", "Time Series Analysis", "Pollutant Correlation", "Air Quality by Station"])

with tab1:
    # Display key metrics based on filters
    st.write(f"**Metrics for {', '.join(selected_stations)} - {selected_aq_category}**")
    category_count_summary = filtered_data['Category'].value_counts().reindex(aq_categories, fill_value=0)
    for category, count in category_count_summary.items():
        st.metric(category, f"{count} Days", delta=f"{count - category_count_summary[category]} from previous")

    # Generate pie chart for air quality category distribution
    fig_pie = px.pie(
        names=category_count_summary.index,
        values=category_count_summary.values,
        title='Distribution of Air Quality Categories'
    )
    st.plotly_chart(fig_pie)

with tab2:
    # Time series visualization for selected pollutants
    selected_pollutant = st.selectbox('Select a Pollutant', air_pollutants)

    # Convert 'timestamp' column to datetime if not already
    filtered_data['timestamp'] = pd.to_datetime(filtered_data['timestamp'])

    # Filter out numeric columns but include the 'timestamp' column for resampling
    numeric_columns = filtered_data.select_dtypes(include=[np.number]).columns.tolist()
    columns_for_resampling = numeric_columns + ['timestamp']
    resample_data = filtered_data[columns_for_resampling]

    # Ensure the DataFrame is not empty before resampling
    if not resample_data.empty:
        timeseries_data = resample_data.resample('M', on='timestamp').mean()
        # Proceed with plotting using timeseries_data
        fig_timeseries = px.line(
            timeseries_data,
            x=timeseries_data.index,
            y=selected_pollutant,
            title=f'Monthly Average of {selected_pollutant}'
        )
        st.plotly_chart(fig_timeseries)
    else:
        st.write("No data available for the selected filters.")

with tab3:
    # Scatter plot for pollutant correlations
    selected_pollutant_x = st.selectbox('Select Pollutant X-Axis', air_pollutants, index=0)
    selected_pollutant_y = st.selectbox('Select Pollutant Y-Axis', air_pollutants, index=1)
    fig_scatter = px.scatter(
        filtered_data,
        x=selected_pollutant_x,
        y=selected_pollutant_y,
        color='station',
        title=f'Correlation between {selected_pollutant_x} and {selected_pollutant_y}'
    )
    st.plotly_chart(fig_scatter)

with tab4:
    # Stacked bar chart for air quality by station
    pivot_counts = filtered_data.pivot_table(
        index='station',
        columns='Category',
        values='PM2.5',
        aggfunc='count',
        fill_value=0
    )
    fig_bar = px.bar(
        pivot_counts,
        x=pivot_counts.index,
        y=aq_categories,
        title='Station-wise Air Quality Distribution',
        labels={'value': 'Count', 'variable': 'Category'},
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig_bar.update_layout(barmode='stack')
    st.plotly_chart(fig_bar)

    # Polar bar chart for wind direction and category
    wind_direction_data = air_quality_data.groupby(['wd', 'Category']).size().reset_index(name='count')
    wind_direction_data['Category_Order'] = wind_direction_data['Category'].map({cat: i for i, cat in enumerate(aq_categories)})
    wind_direction_data_sorted = wind_direction_data.sort_values(by=['Category_Order', 'wd'])

    # Assign colors based on category order
    blues_scale = pc.sequential.Blues_r[:len(aq_categories)]
    fig_polar = go.Figure()
    for i, category in enumerate(aq_categories):
        category_data = wind_direction_data_sorted[wind_direction_data_sorted['Category'] == category]
        fig_polar.add_trace(go.Barpolar(
            r=category_data['count'],
            theta=category_data['wd'],
            name=category,
            marker=dict(color=blues_scale[i])
        ))
    fig_polar.update_layout(title="Wind Direction and Air Quality Category Distribution")
    st.plotly_chart(fig_polar)
    