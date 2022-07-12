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

    self.initialDay = parameters['initialDay'][0].split("/")
    self.finalDay = parameters['initialDay'][1].split("/")