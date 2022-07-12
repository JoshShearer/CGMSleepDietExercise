import glob
import pandas as pd
import numpy as np
import re
from datetime import date, time, datetime, timedelta
from time import sleep
from matplotlib import pyplot as plt
import itertools
from bokeh.io import curdoc, show
from bokeh.models import Label, Legend, LegendItem, LabelSet, Span, BoxAnnotation, ColumnDataSource, ColorBar, BasicTicker,  PrintfTickFormatter, LinearColorMapper, Range1d, Grid, LinearAxis, MultiLine, Plot, layouts
from bokeh.plotting import figure, output_file, show
from bokeh.sampledata.les_mis import data
from bokeh.transform import transform


class CGMProcessing:
    def __init__(self, parameters):
        self.initialDay = datetime.strptime(parameters['dateRange']['initialDay'], '%m/%d/%Y').date()
        self.finalDay = datetime.strptime(parameters['dateRange']['finalDay'], '%m/%d/%Y').date()
        self.filePaths = parameters.get('dataFiles', [])
        self.healthData = []


    def capture_data(self):
        for dataType in self.filePaths:
            print("file", self.filePaths[dataType])
            self.open_file(self.filePaths[dataType], dataType)

        return True

    def open_file(self, file, key):
        data = pd.read_csv(file,encoding = "ISO-8859-1")
        if key == 'ExData':
           data = data.rename(columns={'Time': 'Activity Time'})
        data = data.rename(columns={'DAY' or 'Day': 'Date'})
        data = data.rename(columns={'TIME': 'Time'})
        data['filename'] = filename
        data = clean_date_column(data)
        data = clean_time_column(data)
        data = add_datetime(data)