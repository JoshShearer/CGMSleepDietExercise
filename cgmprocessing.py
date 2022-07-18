import os
import pandas as pd
import numpy as np
from humanfriendly import format_timespan
import re
from scipy.signal import savgol_filter 
from datetime import date, time, datetime, timedelta
from time import sleep
from matplotlib import pyplot as plt
import itertools
from bokeh.layouts import column, row
from bokeh.io import curdoc, show
from bokeh.models import Label, Legend, PreText, LegendItem, LabelSet, Span, BoxAnnotation, ColumnDataSource, ColorBar, BasicTicker,  PrintfTickFormatter, LinearColorMapper, Range1d, Grid, LinearAxis, MultiLine, Plot, layouts
from bokeh.plotting import figure, output_file, show
from bokeh.sampledata.les_mis import data
from bokeh.transform import transform


class CGMProcessing:
    def __init__(self, parameters):
        self.initialDay = self.determine_time(parameters['dateRange']['initialDay'], "initial")
        self.finalDay = self.determine_time(parameters['dateRange']['finalDay'], "final")
        self.filePaths = parameters.get('dataFiles', [])
        self.healthData = {}
        self.analysis = parameters.get('dataAnalysis', [])
        self.adjustments = parameters.get('adjustments')
        self.calWindow = datetime.strptime(str(self.adjustments['calWindow']), '%H').time()
        self.resWindow = datetime.strptime(str(self.adjustments['responseTime']), '%H').time()
        self.minCarbs = self.adjustments['minCarbs']
        self.supplements = parameters['Supplements'] if self.analysis['supplementCorr'] else ''
        self.biometrics = parameters['Biometrics'] if self.analysis['biometricCorr'] else ''
        self.output = parameters['outputFileDirectory']

        
    def determine_time(self, startTime, day):
        timeString = startTime.split(' ')
        if len(timeString) > 1:
            time = datetime.strptime(startTime, '%m/%d/%Y %H:%M')
        else:
            if day == "initial":
                time = datetime.strptime(startTime + ' 0:0', '%m/%d/%Y %H:%M')
            else:
                time = datetime.strptime(startTime + ' 23:59', '%m/%d/%Y %H:%M')
        return time
    
    def capture_data(self):
        for fileType in self.filePaths:
            print("file", self.filePaths[fileType])
            self.open_files(self.filePaths[fileType], fileType)

        return True

    def open_files(self, file, key):
        if key == 'CGMData':
            data = pd.read_csv(file, sep=';')
            data = data.dropna(how='any', subset=['UDT_CGMS'])
        else:
            data = pd.read_csv(file,encoding = "ISO-8859-1")
        if key == 'ExData':
            data = data.rename(columns={'Time': 'Activity Time'})
        if key == "sleepData":
            #convert sleep times from str to DT
            data['Bedtime Start'] = pd.to_datetime(data['Bedtime Start'], format=('%Y-%m-%dT%H:%M:%S-07:00'))
            data['Bedtime End'] = pd.to_datetime(data['Bedtime End'], format=('%Y-%m-%dT%H:%M:%S-07:00'))
        data = data.rename(columns={'DAY' or 'Day' or 'date': 'Date'})
        data = data.rename(columns={'TIME': 'Time'})
        data = self.clean_date_column(data, key)
        data = self.clean_time_column(data)
        data = self.add_datetime(data)
        self.healthData[key] = data

    def clean_date_column(self, df, key):
        #validate date exists
        date = False
        cols = list(df)
        split = False
        for index, column in enumerate(cols):
            if re.match(r"(?i)^(Date|Day)", column):
                date = True
                date_column_index = index
                date_column_name = cols[index]

        if not date:
            return df
        #Check formatting (may have '\' instead of '-' or include time as well
        df.rename(columns={date_column_name:'Date'}, inplace=True)
        df['Date'] = df.Date.str.replace('/' ,'-')
        df['Date'] = df.Date.str.replace('.' ,'-')
        for col in df['Date'].str.contains('\d+-\d+-\d+ \d+', regex=True):  #if time is included col needs to be split
            if col and not split:
                df['str_split'] = df['Date'].str.split(' ')
                df['Date'] = df.str_split.str.get(0)
                df['Time'] = df.str_split.str.get(1)
                del df['str_split']
                split = True
        if key == 'CGMData':
            try:
                df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y', exact=True)
            except:
                df['Date'] = pd.to_datetime(df['Date'], infer_datetime_format=True)
        else:
            df['Date'] = pd.to_datetime(df['Date'], infer_datetime_format=True)
        return df

    def clean_time_column(self, df):
        if 'Time' in df:
            df['Time'] = df['Time'].fillna('00:00:00')
            df['Time'] = pd.to_datetime(df.Time).dt.time

            return df
        else: #Add datetime 00:00:00
            df["Time"] = "00:00:00"
            df['Time'] = pd.to_datetime(df.Time).dt.time
            return df

    def add_datetime(self, df):
        df = df.dropna(how='any', subset=['Time'])
        df['Datetime'] = pd.to_datetime(df['Date'].astype(str)+' '+df['Time'].astype(str))
        df['Datetime'] = pd.to_datetime(df['Datetime'], format=('%Y-%m-%d %I:%M %p'))

        return df

    def clean_data(self):
        dfs = []
        for data in self.healthData:
            if data != 'CGMData':
                self.healthData[data]['data_set'] = data
                dfs.append(self.healthData[data])
            
        self.healthData['combined_Health'] = pd.concat(dfs, ignore_index=True)
        self.healthData['combined_Health']['Date'].fillna(self.healthData['combined_Health']['Date'])
        self.healthData['combined_Health'] = self.healthData['combined_Health'].sort_values(by='Datetime', ascending=True)
        self.healthData['combined_Health'] = self.healthData['combined_Health'].set_index("Date", drop=False)
        self.healthData['CGMData'] = self.healthData['CGMData'].set_index(["Datetime"], drop=False).loc[self.initialDay.strftime('%Y-%m-%d %H:%m:%S'):self.finalDay.strftime('%Y-%m-%d %H:%m:%S'),:]
        if self.analysis['calCorrection']:
            self.healthData['CGMData_original'] = self.healthData['CGMData']
            self.healthData['CGMData'] = self.bg_calibration_correction()
            self.healthData['CGMData'] = self.healthData['CGMData'].set_index("Date", drop=False)
        return

    def extract_time_from_datetime_str(self, day):
        # String should be of the form "2020-02-02 00:00:00"
        day = day.split(' ')
        time = day[1]

        return time
    
    def catch_dt_missing(self, df):
        try:
            df.set_index("Datetime", drop=False).sort_values(['Datetime'], ascending=[True])
        except:
            print("already sorted")
        initial_time = df.iloc[[0]].Datetime
        final_time = df.iloc[[-1]]['Datetime']
        period = self.adjustments['samplePeriod']
        # fart = final_time - initial time
        # time_list = [initial_time + timedelta(minutes=x*period) for x in range(p_range)]
        # df_time_reference = 
        
        return df
        
    def process_mealData(self):
        if self.analysis['matplotlib']:
            self.bg_food_response_matplot()
        if self.analysis['mealStep']:    
            self.bg_food_response_bokeh()
        if self.analysis['exerciseStep']:    
            self.bg_exercise_response_bokeh()
        if self.analysis['heat']:    
            self.bg_heatmap()
        if self.analysis['multiplot']:    
            self.bg_multi_plot()
        if self.analysis['dayOverview']:
            self.bg_daily_overview()
        
        return
    
    def bg_daily_overview(self):
        df_health_data = self.healthData['combined_Health'].set_index("Datetime", drop=False).loc[self.initialDay:self.finalDay,:]
        df_health_data = df_health_data.set_index("Date", drop=False) 
        df_health_data.sort_values(['Datetime'], ascending=[True])
        df_health_data = df_health_data.set_index("Datetime", drop = False)
        df_period_CGM = self.healthData['CGMData'].loc[self.initialDay:self.finalDay,:].set_index(["Datetime"], drop=False)
        # df_period_CGM = df_period_CGM.interpolate(method='linear', limit_direction='both')

        df_response_meals = df_health_data.loc[(df_health_data['data_set'] == 'mealData') & (df_health_data['Carbs (g)'] >= self.adjustments['minCarbs'])]
        df_response_meals = df_response_meals.dropna(how='any', axis=1)
        df_response_meals = df_response_meals.sort_values(['Net Carbs (g)'], ascending=[False])
        
        df_exercise_data = df_health_data.loc[df_health_data['data_set'] == 'ExData']
        df_exercise_data = df_exercise_data.dropna(how='any', axis=1).set_index(['Datetime'], drop=False)
        
        df_sleep_data = self.healthData['sleepData'].set_index("Datetime", drop=False).loc[self.initialDay.date():self.finalDay.date(),:]
        df_sleep_data = df_sleep_data.dropna(how='any', axis=1)
        
        #create an array for all the dates
        num_days = (self.finalDay.date()-self.initialDay.date()).days + 1 #inclusive of last day
        date_list = [self.initialDay + timedelta(days=x) for x in range(num_days)]

        dates = [date_list[x].strftime("%Y-%m-%d") for x in range(len(date_list))]
        
        dir_path = (self.output + os.path.sep + 'bokeh_daily_overview')
        if not os.path.isdir(dir_path):
            os.mkdir(dir_path)
            
        for date in dates:
            # output to static HTML file
            output_file(dir_path + os.path.sep + 'Daily Overview ' + '(' + date + ')' + '.html')
            columns = []
            # create a new plot
            p = figure(
            tools="pan,box_zoom,reset,save",
            title="log axis example", x_axis_type='datetime',
            x_axis_label='Response', y_axis_label='Glucose'
            )
            try:
                df_date_exercise = df_exercise_data[df_exercise_data['Date'].dt.strftime("%Y-%m-%d") == date]
                
                if not df_date_exercise.empty:                
                    exercise_table = PreText(text='', width=500)
                    exercise_table.text = str(df_date_exercise[["Time", "Activity Type", "Title", "Calories", "Max HR", "Avg HR", "Activity Time"]].to_string())
                    columns.append(exercise_table)
                    for time, workout in df_exercise_data.iterrows():
                        determine_time = workout['Datetime']
                        end_time = determine_time + timedelta(minutes=20)
                        exercise_box = BoxAnnotation(left=determine_time, right=end_time, fill_alpha=0.4, fill_color='blue')
                        p.add_layout(exercise_box)
            except:
                print("No exercise data for " + date)
            
            
            df_date_CGM = df_period_CGM[df_period_CGM['Date'].dt.strftime("%Y-%m-%d") == date]
            try:
                df_date_meals = df_response_meals[df_response_meals['Date'].dt.strftime("%Y-%m-%d") == date].sort_values(['Time'], ascending=[True])
                
                if not df_date_meals.empty:
                    meal_table = PreText(text='', width=500)
                    df_date_meals = df_date_meals.filter(["Time", "Food Name", "Energy (kcal)", "Group", "Net Carbs (g)"])
                    meal_table.text = str(df_date_meals[["Time", "Food Name", "Energy (kcal)", "Group", "Net Carbs (g)"]].to_string())
                    columns.append(meal_table)
                    
                    for time, meal in df_response_meals.iterrows():
                        determine_time = meal['Datetime']
                        end_time = determine_time + timedelta(minutes=20)
                        meal_box = BoxAnnotation(left=determine_time, right=end_time, fill_alpha=0.4, fill_color='red')
                        p.add_layout(meal_box)
            except:
                print("This appears to be a fasting day " + date)
            
            sleep_table = PreText(text='', width=500)
            df_date_sleep = df_sleep_data[df_sleep_data['Date'].dt.strftime("%Y-%m-%d") == date]
            if not df_date_sleep.empty:
                df_date_sleep = df_date_sleep.filter(["Sleep Score", "Readiness Score", "Bedtime Start", "Bedtime End"]) 
                sleep_time = df_date_sleep["Bedtime End"].dt.to_pydatetime() - df_date_sleep["Bedtime Start"].dt.to_pydatetime()
                df_date_sleep["Total Sleep"] = format_timespan(sleep_time[0])  
                sleep_table.text = str(df_date_sleep[["Sleep Score", "Readiness Score", "Bedtime Start", "Bedtime End", "Total Sleep"]].to_string())
                columns.append(sleep_table)
            

            wl = len(df_date_CGM) -1
            if not wl % 2:
                wl = len(df_date_CGM) - 2
            pOrder = 9 if (9 < wl-1) else (wl-1)
            df_date_CGM_filtered = df_date_CGM[['UDT_CGMS']].apply(savgol_filter, window_length=(wl), polyorder=(pOrder))
            p.line(df_date_CGM["Datetime"], df_date_CGM.UDT_CGMS, line_width=4, line_color="black")

            # show the results
            low_box = BoxAnnotation(top=70, fill_alpha=0.1, fill_color='red')
            mid_box = BoxAnnotation(bottom=70, top=140, fill_alpha=0.1, fill_color='green')
            high_box = BoxAnnotation(bottom=140, fill_alpha=0.1, fill_color='red')

            p.add_layout(low_box)
            p.add_layout(mid_box)
            p.add_layout(high_box)

            # delta = df_meal_CGM.UDT_CGMS.max() - df_meal_CGM.UDT_CGMS[0]
            height = int(df_date_CGM.UDT_CGMS.max()*.95)
            height2 = int(df_date_CGM.UDT_CGMS.max()*.93)
            height3 = int(df_date_CGM.UDT_CGMS.max()*.90)
            height4 = int(df_date_CGM.UDT_CGMS.max()*.87)

            p.title.text = "Glucose Response Full Day Overview " + date
            p.title.align = "center"
            p.xgrid[0].grid_line_color=None
            p.ygrid[0].grid_line_alpha=0.5
            p.xaxis.axis_label = date
            p.yaxis.axis_label = 'mmol/dl'
            # show(p)
            show(row(p, column(columns)))
            # sleep(1)

       
        print("Daily Overview completed")

    def bg_food_response_matplot(self):
        current_date = self.initialDay.date()
        while current_date <= self.finalDay.date():
            print("Processing Data for " + str(current_date))
            df_current_day = self.healthData['combined_Health'].set_index("Date", drop=False).loc[current_date,:]
            df_current_day.sort_values(['Datetime'], ascending=[True])
            df_current_day = df_current_day.set_index("Datetime", drop = False)
            df_current_day_CGM = self.healthData['CGMData'].set_index("Date", drop=False).loc[current_date,:]
            df_current_day_CGM.sort_values(['Datetime'], ascending=[True])
            df_current_day_CGM = df_current_day_CGM.set_index("Datetime", drop=False)

            response_meals = df_current_day.loc[(df_current_day['data_set'] == 'mealData') & (df_current_day['Carbs (g)'] >= self.minCarbs)]
            sleep_data = df_current_day.loc[df_current_day['data_set'] == 'sleepData']
            exercise_data = df_current_day.loc[df_current_day['data_set'] == 'ExData']
            response_meals = response_meals.dropna(how='any', axis=1)
            sleep_data = sleep_data.dropna(how='any', axis=1)
            exercise_data = exercise_data.dropna(how='any', axis=1)
            nrows = len(response_meals)
            extra_row = nrows % 2
            if extra_row:
                fig, axes = plt.subplots(nrows//2+1,2)
            else:
                fig, axes = plt.subplots(nrows//2,2)

            index = 0
            for food in response_meals.iterrows():
                df_meal_data = food[1]
                period_start = df_meal_data.Datetime.to_pydatetime()
                period_start_str = self.extract_time_from_datetime_str(str(pd.to_datetime(period_start)))
                period_end = period_start + timedelta(hours=self.resWindow.hour)
                period_end_str = self.extract_time_from_datetime_str(str(pd.to_datetime(period_end)))
                df_CGM_response = df_current_day_CGM.between_time(period_start_str,period_end_str)
                df_exercise = exercise_data.between_time(period_start_str,period_end_str)

                wl = len(df_CGM_response) -1
                if not wl % 2:
                    wl = len(df_CGM_response) - 2
                pOrder = 9 if (9 < wl-1) else (wl-1)
                df_CGM_response["filtered"] = df_CGM_response[['UDT_CGMS']].apply(savgol_filter, window_length=(wl), polyorder=(pOrder))

                if len(df_CGM_response) == 0:
                    continue
                title = (str(df_CGM_response['Date'].values[0]) + " Time (Day)")

                df_CGM_response.plot(x='Time', y='filtered', ax=axes[index//2,1 if index % 2 else 0], subplots=True)

                if not df_exercise.empty:
                    for workout in df_exercise.iterrows():
                        activity_info = workout[1]
                        activity_time = pd.to_datetime(activity_info['Activity Time'])
                        activity_time = activity_time.to_pydatetime()
                        determine_time = activity_info.Datetime.to_pydatetime()
                        end_time = determine_time + timedelta(hours=activity_time.hour, minutes=activity_time.minute)
                        axes[index//2,1 if index % 2 else 0].axvspan(str(determine_time), str(end_time), color='blue', alpha=0.5)
                        axes[index//2,1 if index % 2 else 0].annotate(activity_info.Title + '\n' + activity_info['Calories'] + ' Calories Burned', xy=(str(determine_time),df_CGM_response['UDT_CGMS'].median()))

                axes[index//2,1 if index % 2 else 0].set_title('BG Response to ' + df_meal_data.loc['Food Name'])
                axes[index//2,1 if index % 2 else 0].set_xlabel(str(df_CGM_response['Date'].values[0]) + " Time(Day)")
                axes[index//2,1 if index % 2 else 0].set_ylabel("Blood Glucose")
                index += 1

            plt.tight_layout()
            plt.show()
            current_date = current_date + timedelta(days=1)
        return

    def bg_exercise_response_bokeh(self):
        df_health_data = self.healthData['combined_Health'].set_index("Datetime", drop=False).loc[self.initialDay:self.finalDay,:]
        df_health_data = df_health_data.set_index("Date", drop=False) 
        df_health_data.sort_values(['Datetime'], ascending=[True])
        df_health_data = df_health_data.set_index("Datetime", drop = False)
        df_period_CGM = self.healthData['CGMData'].set_index("Datetime", drop=False).loc[self.initialDay.strftime("%Y-%m-%d"):self.finalDay.strftime("%Y-%m-%d"),:]

        response_meals = df_health_data.loc[(df_health_data['data_set'] == 'mealData') & (df_health_data['Carbs (g)'] >= self.adjustments['minCarbs'])]
        response_meals = response_meals.set_index("Datetime", drop=False)
        response_meals = response_meals.dropna(how='any', axis=1)
        # response_meals = response_meals.sort_values(['Carbs (g)'], ascending=[False])
        exercise_data = df_health_data.loc[df_health_data['data_set'] == 'ExData']
        exercise_data = exercise_data.set_index("Datetime", drop=False)
        exercise_data = exercise_data.dropna(how='any', axis=1)

        dir_path = (self.output + os.path.sep + 'bokeh_step_responses_exercise')
        if not os.path.isdir(dir_path):
            os.mkdir(dir_path)
        for time, workout in exercise_data.iterrows():
            # output to static HTML file
            name_string = workout['Title']
            re.sub('[^a-zA-Z0-9 \n\.]', '', name_string)
            
            output_file(dir_path + os.path.sep + name_string + '(' +time.strftime("%Y_%m_%d") + ')' +'.html')

            # create a new plot
            p = figure(
            tools="pan,box_zoom,reset,save",
            title="log axis example", x_axis_type='datetime',
            x_axis_label='Response', y_axis_label='Glucose'
            )


            # add some renderers
            determine_time = workout.Datetime - timedelta(minutes=30)
            end_time = determine_time + timedelta(hours=self.resWindow.hour) + timedelta(hours=1)
            df_exercise_CGM = df_period_CGM.loc[determine_time.strftime("%Y-%m-%d %H:%M:%S"):end_time.strftime("%Y-%m-%d %H:%M:%S"),:]
            # df_exercise_CGM = self.catch_dt_missing(df_exercise_CGM)
            df_meal_exercise = response_meals.loc[determine_time:end_time,:]
            try:
                the_beginning = pd.to_datetime(df_exercise_CGM.iloc[0]['Datetime']).to_pydatetime()
            except: #Missing Data at times due to lack of sensor
                print('Data Failure, abandoning ' + workout['Title'] + ' Date => ' + workout['Date'].strftime("%Y-%m-%d"))
                continue
            the_beginning = the_beginning.time()
                
            #for cases where data is missing, need to fill in data or plot may not load
            # df_exercise_CGM.set_index("Datetime", drop=False).resample()
            wl = len(df_exercise_CGM) -1
            if not wl % 2:
                wl = len(df_exercise_CGM) - 2
            pOrder = 9 if (9 < wl-1) else (wl-1)
            df_exercise_CGM_filtered = df_exercise_CGM[['UDT_CGMS']].apply(savgol_filter, window_length=(wl), polyorder=(pOrder))
            p.line(df_exercise_CGM["Datetime"], df_exercise_CGM_filtered.UDT_CGMS, line_width=4, line_color="black")

            activity_info = workout
            activity_time = pd.to_datetime(activity_info['Activity Time'])
            activity_time = activity_time.to_pydatetime()
            determine_time = activity_info.Datetime.to_pydatetime()
            end_time = determine_time + timedelta(hours=activity_time.hour, minutes=activity_time.minute)
            exercise_box = BoxAnnotation(left=determine_time, right=end_time, fill_alpha=0.4, fill_color='blue')
            columns = []
            
            # try:
            exercise_table = PreText(text='', width=500)
            exercise_table.text = str(workout[["Time", "Activity Type", "Title", "Calories", "Max HR", "Avg HR", "Activity Time"]].to_string())
            columns.append(exercise_table)
            # except:
            #     print("Problems reading exercise data " + str(time))
            
            try:
                df_meals = df_meal_exercise.sort_values(['Time'], ascending=[True]).filter(["Time", "Food Name", "Energy (kcal)", "Group", "Net Carbs (g)"])
                if not df_meals.empty:
                    meal_table = PreText(text='', width=500)
                    meal_table.text = str(df_meals[["Time", "Food Name", "Energy (kcal)", "Group", "Net Carbs (g)"]].to_string())
                    columns.append(meal_table)
            except:
                print("This appears to be a fasting day " + str(time))
            
            for time, meal in df_meal_exercise.iterrows():
                meal_start = time
                meal_end = meal_start + timedelta(minutes=20)                
                meal_box = BoxAnnotation(left=meal_start, right=meal_end, fill_alpha=0.4, fill_color='red')
                p.add_layout(meal_box)
            label1 = Label(x=300, y=int(df_exercise_CGM.UDT_CGMS.min()*1.2), x_units='screen', text="Activity = " + str(workout.Title), render_mode='css',
                border_line_color='black', border_line_alpha=1.0,
                background_fill_color='white', background_fill_alpha=1.0)
            label2 = Label(x=300, y=int(df_exercise_CGM.UDT_CGMS.min()*1.1), x_units='screen', text='Calories = ' + str(workout.Calories), render_mode='css',
                border_line_color='black', border_line_alpha=1.0,
                background_fill_color='white', background_fill_alpha=1.0)
            p.add_layout(exercise_box)
            p.add_layout(label1)
            p.add_layout(label2)
            # show the results
            low_box = BoxAnnotation(top=70, fill_alpha=0.1, fill_color='red')
            mid_box = BoxAnnotation(bottom=70, top=140, fill_alpha=0.1, fill_color='green')
            high_box = BoxAnnotation(bottom=140, fill_alpha=0.1, fill_color='red')

            p.add_layout(low_box)
            p.add_layout(mid_box)
            p.add_layout(high_box)

            delta = df_exercise_CGM.UDT_CGMS.max() - df_exercise_CGM.UDT_CGMS[0]
            height = int(df_exercise_CGM.UDT_CGMS.max()*.95)
            height2 = int(df_exercise_CGM.UDT_CGMS.max()*.93)
            label3 = Label(x=70, y=height, x_units='screen', text="Glucose Delta = -" + str(delta), render_mode='css',
            border_line_color='black', border_line_alpha=1.0,
            background_fill_color='white', background_fill_alpha=1.0)
            label4 = Label(x=70, y=height2, x_units='screen', text='Peak = ' + str(df_exercise_CGM.UDT_CGMS.max()) + ' mmol/dl', render_mode='css',
            border_line_color='black', border_line_alpha=1.0,
            background_fill_color='white', background_fill_alpha=1.0)
            
            p.add_layout(label3)
            p.add_layout(label4)
            p.title.text = "Glucose Response of " + workout['Title']
            p.title.align = "center"
            p.xgrid[0].grid_line_color=None
            p.ygrid[0].grid_line_alpha=0.5
            p.xaxis.axis_label = 'Time (' + str(workout['Date']) + ')'
            p.yaxis.axis_label = 'mmol/dl'
            show(row(p, column(columns)))
            # sleep(1)
        print('just wait until I finish')
    
    def bg_heatmap(self):

        num_days = (self.finalDay.date()-self.initialDay.date()).days + 1 #inclusive of last day
        date_list = [self.initialDay + timedelta(days=x) for x in range(num_days)]

        #create an array for all the dates and times to
        time_index = []
        min_time = datetime.min.time()
        min_datetime = datetime.combine(date_list[0], min_time)
        time_list = [min_datetime + timedelta(minutes=x*15) for x in range(96)]
        time_index = [time_list[x].strftime("%H:%M:%S") for x in range(len(time_list))]
        date_column = [date_list[x].strftime("%Y-%m-%d") for x in range(len(date_list))]

        # Prep matrices for data filling.  All data necessary to fill
        df_CGM_period_max = self.healthData['CGMData'].set_index(self.healthData['CGMData']['Datetime'])
        df_CGM_end_test = df_CGM_period_max.loc[df_CGM_period_max['Date'].dt.strftime("%Y-%m-%d") == self.finalDay.date().strftime("%Y-%m-%d")]
        df_CGM_initial_test = df_CGM_period_max.loc[df_CGM_period_max['Date'] == self.initialDay.date().strftime("%Y-%m-%d")]
        df_CGM_period_max = df_CGM_period_max.set_index('Datetime', drop=False)
        df_CGM_period_max = df_CGM_period_max.resample('15Min', base=15, label='right')['UDT_CGMS'].max().sort_values()
        df_CGM_end_test= df_CGM_end_test.resample('15Min', base=15, label='right')['UDT_CGMS'].max()
        df_CGM_initial_test= df_CGM_initial_test.resample('15Min', base=15, label='right')['UDT_CGMS'].max()

        # Fill in missing data if necessary
        if len(df_CGM_end_test.index) < len(time_index):
            for day in date_list:
                day = day.date()
                if day == self.finalDay.date():
                    for index in time_list:
                        try:
                            df_CGM_end_test[datetime.combine(self.finalDay.date(),index.time())]
                        except:
                            df_CGM_end_test[datetime.combine(self.finalDay.date(),index.time())] = np.nan
            df_CGM_end_period_max = self.CGM_fill_decay(df_CGM_end_test, 'forward')
            df_CGM_period_max = df_CGM_period_max.sort_values().loc[(self.initialDay).strftime("%Y-%m-%d"):(self.finalDay - timedelta(days=1)).strftime("%Y-%m-%d")]
            df_CGM_period_max = pd.concat([df_CGM_period_max, df_CGM_end_period_max])
        if len(df_CGM_initial_test.index) < len(time_index):
            for day in date_list:
                day = day.date()
                if day == self.initialDay.date():
                    for index in time_list:
                        try:
                            df_CGM_initial_test[datetime.combine(self.initialDay.date(),index.time())]
                        except:
                            df_CGM_initial_test[datetime.combine(self.initialDay.date(),index.time())] = np.nan
            df_CGM_initial_period_max = self.CGM_fill_decay(df_CGM_initial_test.sort_index(), 'backward')
            df_CGM_period_max = df_CGM_period_max.sort_values().loc[(self.initialDay + timedelta(days=1)).strftime("%Y-%m-%d"):(self.finalDay).strftime("%Y-%m-%d")]
            df_CGM_period_max = pd.concat([df_CGM_period_max, df_CGM_initial_period_max])
        #Remove redundant time indices
        idx = np.unique( df_CGM_period_max.index.values, return_index = True )[1]
        df_CGM_period_max = df_CGM_period_max.iloc[idx]

        df_meals = self.healthData['combined_Health'].loc[self.healthData['combined_Health']['data_set'] == 'mealData'].set_index('Datetime', drop=False)
        df_meals = df_meals.dropna(how='all', axis=1) # drop all fully nan columns as they are not useful here
        df_dt_matrix_CGM = pd.DataFrame(0, columns=date_column, index=time_index)
        df_dt_matrix_meals = pd.DataFrame(0, columns=date_column, index=time_index)
        
        for date, date_array in df_dt_matrix_CGM.iteritems():
                
            date_array = date_array.reset_index()
            df_meals_day = df_meals.loc[df_meals['Date'] == date] #& (df_current_day['Carbs (g)'] >= 5)
            df_meals_day = df_meals_day.set_index(df_meals_day['Datetime'])

            for time_i in range(date_array.shape[0]):
                #df of the current time period for pertinent information
                current_period_time = pd.to_datetime(date_array.loc[time_i,'index'])
                current_period_time_str = self.extract_time_from_datetime_str(str(current_period_time))
                if time_i < date_array.shape[0]-1:
                    next_period_time = pd.to_datetime(date_array.loc[time_i + 1,'index'])
                    next_period_time_str = self.extract_time_from_datetime_str(str(next_period_time))

                current_time = current_period_time.to_pydatetime().time()
                current_dt = datetime.combine(datetime.strptime(date, "%Y-%m-%d") , current_time)
                next_time = next_period_time.to_pydatetime().time()
                next_dt = datetime.combine(datetime.strptime(date, "%Y-%m-%d"), next_time)
                try:
                    CGM_max = df_CGM_period_max[current_dt]
                except Exception as e:
                    try:
                        CGM_max = df_CGM_period_max[next_dt]
                    except Exception as e:
                        CGM_max = df_CGM_period_max[previous_dt]
                        print("error deriving BG, need bug fix")
                        continue

                df_dt_matrix_CGM.loc[current_period_time_str, date] = CGM_max
                meal_string = ''
                df_meals_day = df_meals_day.sort_values(['Carbs (g)'], ascending=[False])
                for time, meal in df_meals_day.iterrows():
                    meal_time = datetime.combine(datetime.strptime(date, "%Y-%m-%d"), meal.Time)
                    time_diff = meal_time + timedelta(hours=self.resWindow.hour)
                    if (time_diff > current_dt and current_dt >= meal_time):
                        meal_string += meal['Food Name'] + ' + '
                df_dt_matrix_meals.loc[current_period_time_str, date] = meal_string

                previous_dt = current_dt
            print('Day ' + date + ' finished')
        df_dt_matrix_CGM = df_dt_matrix_CGM.interpolate(method='linear', limit_direction='forward', axis=1)#method='polynomial', order=2) 
        print("wait!")

        total_days = df_dt_matrix_CGM.shape[1]
        
        xname = [[date_column[j] for i in range(len(time_index))] for j in range(len(date_column))]
        yname = [[time_index[i] for i in range(len(time_index))] for j in range(len(date_column))]
        xname = list(itertools.chain.from_iterable(xname))
        yname = list(itertools.chain.from_iterable(yname))
        bg_list = list(df_CGM_period_max.interpolate(method='linear', limit_direction='both'))
        min = df_CGM_period_max.min()
        def calc_color(bg):
            colormap = ["#004529", "#006d2c", "#238b45", "#d9f0a3", "#fed976", "#feb24c",
                    "#fd8d3c", "#fc4e2a", "#e31a1c", "#bd0026", "#800026"]
            if bg < 60:
                color = (colormap[0])
            elif bg > 160:
                color = (colormap[10])
            else:
                color = (colormap[int(((bg-60)/100)*10)])
            return color

        color_selection = ["#004529", "#006d2c", "#238b45", "#d9f0a3", "#fed976", "#feb24c", "#fd8d3c", "#fc4e2a", "#e31a1c", "#bd0026", "#800026"]
        mapper = LinearColorMapper(palette=color_selection, low=60, high=180)#low=df_CGM_period_max.min(), high=df_CGM_period_max.min())
        color = map(calc_color, bg_list)
        color = list(color)
        food_list = list(itertools.chain.from_iterable(df_dt_matrix_meals.transpose().values.tolist()))
        xydata = {'xname': xname, 'yname': yname, 'bg': bg_list, 'foods': food_list}
        source = ColumnDataSource(xydata)
        data=dict(
            xname=xname,
            yname=yname,
            colors=color,
            bg=bg_list,
            foods=food_list,
        )

        p = figure(title="Blood Glucose over " + str(total_days) + " days",
                x_axis_location="above", tools="hover,pan,box_zoom,reset,save",
                x_range=date_column, y_range=time_index, output_backend="webgl",
                tooltips=[('Sample', '@yname, @xname'), ('Foods', '@foods'), ('Blood Glucose', '@bg')])

        p.plot_width = 1200
        p.plot_height = 800
        p.grid.grid_line_color = None
        p.axis.axis_line_color = None
        p.axis.major_tick_line_color = None
        p.axis.major_label_text_font_size = "7px"
        p.axis.major_label_standoff = 0
        p.xaxis.major_label_orientation = np.pi/3

        p.rect('xname', 'yname', 0.9, 0.9, source=data,
            color='colors',
            line_color=None,
            hover_line_color='black', hover_color='colors',
            )

        output_file(self.output + os.path.sep + "bgheatmap.html", title="BG Heatmap")

        color_bar = ColorBar(color_mapper=mapper, location=(0, 0),
                            ticker=BasicTicker(desired_num_ticks=len(color_selection)-2),
                            formatter=PrintfTickFormatter(format="%d"))

        p.add_layout(color_bar, 'right')
        p.add_layout(color_bar, 'left')
        show(p) # show the plot
        print('just wait until I finish')

    def bg_food_response_bokeh(self):
        df_health_data = self.healthData['combined_Health'].set_index("Datetime", drop=False).loc[self.initialDay:self.finalDay,:]
        df_health_data = df_health_data.set_index("Date", drop=False) 
        df_health_data.sort_values(['Datetime'], ascending=[True])
        df_health_data = df_health_data.set_index("Datetime", drop = False)
        df_period_CGM = self.healthData['CGMData'].set_index("Datetime", drop=False).loc[self.initialDay.strftime("%Y-%m-%d"):self.finalDay.strftime("%Y-%m-%d"),:]

        response_meals = df_health_data.loc[(df_health_data['data_set'] == 'mealData') & (df_health_data['Carbs (g)'] >= self.adjustments['minCarbs'])]
        exercise_data = df_health_data.loc[df_health_data['data_set'] == 'ExData']
        exercise_data = exercise_data.set_index("Datetime", drop=False)
        exercise_data = exercise_data.dropna(how='any', axis=1)
        response_meals = response_meals.dropna(how='any', axis=1)
        response_meals = response_meals.sort_values(['Carbs (g)'], ascending=[False])

        dir_path = (self.output + os.path.sep + 'bokeh_step_responses_meals')
        if not os.path.isdir(dir_path):
            os.mkdir(dir_path)
        for time, meal in response_meals.iterrows():
            # output to static HTML file
            name_string = meal['Food Name']
            name_string = re.sub('[^a-zA-Z0-9 \n\.]', '', name_string)
            
            output_file(dir_path + os.path.sep + name_string + '(' +time.strftime("%Y_%m_%d") + ')' + '.html')

            # create a new plot
            p = figure(
            tools="pan,box_zoom,reset,save",
            title="log axis example", x_axis_type='datetime',
            x_axis_label='Response', y_axis_label='Glucose'
            )


            # add some renderers
            determine_time = meal.Datetime
            end_time = determine_time + timedelta(hours=self.resWindow.hour)
            df_meal_CGM = df_period_CGM.loc[determine_time.strftime("%Y-%m-%d %H:%M:%S"):end_time.strftime("%Y-%m-%d %H:%M:%S"),:]
            if len(df_meal_CGM) < 10:
                continue
            wl = (len(df_meal_CGM) - 1) 
            if not wl % 2:
                wl = len(df_meal_CGM) - 2
            pOrder = 9 if (9 < wl-1) else (wl-1)
            df_meal_CGM_filtered = df_meal_CGM[['UDT_CGMS']].apply(savgol_filter, window_length=(wl), polyorder=(pOrder))
            df_meal_exercise = exercise_data.loc[determine_time:end_time,:]
            try:
                the_beginning = pd.to_datetime(df_meal_CGM.iloc[0]['Datetime']).to_pydatetime()
            except: #Missing Data at times due to lack of sensor
                print('Data Failure, abandoning ' + meal['Food Name'] + ' Date => ' + meal['Date'].strftime("%Y-%m-%d"))
                continue
            the_beginning = the_beginning.time()
            df_meal_CGM["Response Time"] = df_meal_CGM.Datetime - timedelta(hours=the_beginning.hour, minutes=the_beginning.minute, seconds=the_beginning.second)
            df_meal_CGM["Response Time"] = df_meal_CGM["Response Time"].dt.time
            df_meal_CGM["ZeroedCGMS"] = df_meal_CGM.UDT_CGMS - df_meal_CGM.iloc[0]["UDT_CGMS"]
            p.line(df_meal_CGM["Datetime"], df_meal_CGM_filtered.UDT_CGMS, line_width=4, line_color="black")

            if not df_meal_exercise.empty:
                for time, workout in df_meal_exercise.iterrows():
                    activity_info = workout
                    activity_time = pd.to_datetime(activity_info['Activity Time'])
                    activity_time = activity_time.to_pydatetime()
                    determine_time = activity_info.Datetime.to_pydatetime()
                    end_time = determine_time + timedelta(hours=activity_time.hour, minutes=activity_time.minute)
                    exercise_box = BoxAnnotation(left=determine_time, right=end_time, fill_alpha=0.4, fill_color='blue')
                    label5 = Label(x=300, y=int(df_meal_CGM.UDT_CGMS.min()*1.2), x_units='screen', text="Activity = " + str(workout.Title), render_mode='css',
                        border_line_color='black', border_line_alpha=1.0,
                        background_fill_color='white', background_fill_alpha=1.0)
                    label6 = Label(x=300, y=int(df_meal_CGM.UDT_CGMS.min()*1.1), x_units='screen', text='Calories = ' + str(workout.Calories), render_mode='css',
                        border_line_color='black', border_line_alpha=1.0,
                        background_fill_color='white', background_fill_alpha=1.0)
                    p.add_layout(exercise_box)
                    p.add_layout(label5)
                    p.add_layout(label6)
            # show the results
            low_box = BoxAnnotation(top=70, fill_alpha=0.1, fill_color='red')
            mid_box = BoxAnnotation(bottom=70, top=140, fill_alpha=0.1, fill_color='green')
            high_box = BoxAnnotation(bottom=140, fill_alpha=0.1, fill_color='red')

            p.add_layout(low_box)
            p.add_layout(mid_box)
            p.add_layout(high_box)

            delta = df_meal_CGM.UDT_CGMS.max() - df_meal_CGM.UDT_CGMS[0]
            height = int(df_meal_CGM.UDT_CGMS.max()*.95)
            height2 = int(df_meal_CGM.UDT_CGMS.max()*.93)
            height3 = int(df_meal_CGM.UDT_CGMS.max()*.90)
            height4 = int(df_meal_CGM.UDT_CGMS.max()*.87)
            label1 = Label(x=70, y=height, x_units='screen', text="Glucose Delta = " + str(delta), render_mode='css',
            border_line_color='black', border_line_alpha=1.0,
            background_fill_color='white', background_fill_alpha=1.0)
            label2 = Label(x=70, y=height2, x_units='screen', text='Peak = ' + str(df_meal_CGM.UDT_CGMS.max()) + ' mmol/dl', render_mode='css',
            border_line_color='black', border_line_alpha=1.0,
            background_fill_color='white', background_fill_alpha=1.0)
            label3 = Label(x=70, y=height3, x_units='screen', text='Total Carbs = ' + str(meal['Carbs (g)']) + ' g', render_mode='css',
            border_line_color='black', border_line_alpha=1.0,
            background_fill_color='white', background_fill_alpha=1.0)
            label4 = Label(x=70, y=height4, x_units='screen', text='Total Calories = ' + str(meal['Energy (kcal)']), render_mode='css',
            border_line_color='black', border_line_alpha=1.0,
            background_fill_color='white', background_fill_alpha=1.0)

            p.add_layout(label1)
            p.add_layout(label2)
            p.add_layout(label3)
            p.add_layout(label4)
            p.title.text = "Glucose Response of " + meal['Food Name']
            p.title.align = "center"
            p.xgrid[0].grid_line_color=None
            p.ygrid[0].grid_line_alpha=0.5
            p.xaxis.axis_label = 'Time (' + str(meal['Date']) + ')'
            p.yaxis.axis_label = 'mmol/dl'
            show(p)
            # sleep(1)
        print('just wait until I finish')

    #This function assuming blocks of missing data moving in universal direction ie front or back of df
    def CGM_fill_decay(self, _df, _dir):
        count = _df.isna().sum()
        baseline = 88   #This is avg baseline Blood Glucose
        decay_window = 8 #typical decay time is 1 hour
        i = 0
        if _dir == 'forward':
            first_nan = _df.size - count
            glucose = _df[first_nan-1]
            decay_rate = (glucose - baseline)/decay_window
            for index in range(count):
                new_glucose = glucose - (decay_rate*index)
                if new_glucose < baseline:
                    new_glucose = baseline
                _df[first_nan + index] = int(new_glucose)
        else:
            ramp = count - decay_window
            glucose = _df[count]
            decay_rate = (glucose - baseline)/decay_window
            for index in range(count):
                if index > ramp:
                    i+=1
                    new_glucose = baseline + (decay_rate*i)
                    _df[index] = int(new_glucose)
                else:
                    _df[index] = baseline
        return _df
        
    def bg_multi_plot(self):
        # prepare some data
        df_health_data = self.healthData['combined_Health'].set_index("Datetime", drop=False).loc[self.initialDay:self.finalDay,:]
        df_health_data = df_health_data.set_index("Date", drop=False) 
        df_health_data.sort_values(['Datetime'], ascending=[True])
        df_health_data = df_health_data.set_index("Datetime", drop = False)
        df_period_CGM = self.healthData['CGMData'].set_index("Datetime", drop=False).loc[self.initialDay.strftime("%Y-%m-%d"):self.finalDay.strftime("%Y-%m-%d"),:]

        response_meals = df_health_data.loc[(df_health_data['data_set'] == 'mealData') & (df_health_data['Carbs (g)'] >= self.adjustments['minCarbs'])]
        exercise_data = df_health_data.loc[df_health_data['data_set'] == 'ExData']
        exercise_data = exercise_data.set_index("Datetime", drop=False)
        exercise_data = exercise_data.dropna(how='any', axis=1)
        response_meals = response_meals.dropna(how='any', axis=1)
        response_meals = response_meals.sort_values(['Carbs (g)'], ascending=[False])


        p = figure(
        tools="pan,box_zoom,hover,reset,save",
        title="Multiline CGM", x_axis_type='datetime',
        x_axis_label='Response', y_axis_label='Glucose',
        y_range = (-100, 120), y_axis_location='right',
        tooltips=[('Sample', '@xname, @yname'), ('Glucose Delta', '@GD'), ('Max Blood Glucose', '@bg'),
                    ('Total Calories', '@cal'),('Total Carbs', '@carb'),('Food', '@Food')],
        y_minor_ticks=2,output_backend="webgl"
        )
        # current_date = current_date + timedelta(days=1)
        output_file(self.output + os.path.sep +'Multiplot.html')
        df_plot_data = pd.DataFrame(columns=['Date','Meal','Time','Glucose'])
        df_data_summary = pd.DataFrame(columns=['Date','Time','Meal','Peak Glucose','Glucose Delta', 'Calories','Carbs'])
        for meal_time, meal in response_meals.iterrows():
            # output to static HTML file
            name_string = meal['Food Name']
            name_string = name_string.split(', ')
            determine_time = meal.Datetime
            end_time = determine_time + timedelta(hours=self.resWindow.hour)
            df_meal_CGM = df_period_CGM.loc[determine_time:end_time,:]
            df_meal_exercise = exercise_data.loc[determine_time:end_time,:]

            try:
                the_beginning = pd.to_datetime(df_meal_CGM.iloc[0]['Datetime']).to_pydatetime()
            except: #Missing Data at times due to lack of sensor
                print('Data Failure, abandoning ' + meal['Food Name'] + ' Date => ' + meal['Date'].strftime("%Y-%m-%d"))
                continue
            the_beginning = the_beginning.time()
            df_meal_CGM["Response Time"] = df_meal_CGM.Datetime - timedelta(hours=the_beginning.hour, minutes=the_beginning.minute, seconds=the_beginning.second)
            df_meal_CGM["Response Time"] = df_meal_CGM["Response Time"].dt.time
            df_meal_CGM["ZeroedCGMS"] = df_meal_CGM.UDT_CGMS - df_meal_CGM.iloc[0]["UDT_CGMS"]
            if len(df_meal_CGM) < 10:
                continue
            wl = len(df_meal_CGM) -1
            if not wl % 2:
                wl = len(df_meal_CGM) - 2
            pOrder = 9 if (9 < wl-1) else (wl-1)
            df_meal_CGM["filtered"] = df_meal_CGM[['ZeroedCGMS']].apply(savgol_filter, window_length=(wl), polyorder=(pOrder))
            
            df_temp = pd.DataFrame({'Date':[meal_time],'Meal':[name_string[0]],'Time':[list(df_meal_CGM["Response Time"])],'Glucose':[list(df_meal_CGM.ZeroedCGMS)]})
            df_plot_data = df_plot_data.append(df_temp)
            meal['Delta'] = df_meal_CGM.UDT_CGMS.max() - df_meal_CGM.UDT_CGMS[0]
            meal['Peak'] = df_meal_CGM.UDT_CGMS.max()
            xydata = {'RespTime': df_meal_CGM["Response Time"], 'zg': df_meal_CGM.filtered,
                    'xname': [meal['Date'].strftime("%Y-%m-%d") for i in range(len(df_meal_CGM.ZeroedCGMS))],
                    'yname': [meal['Time'].strftime("%H:%M:%S") for i in range(len(df_meal_CGM.ZeroedCGMS))],
                    'bg': [str(int(meal['Peak'])) for i in range(len(df_meal_CGM.ZeroedCGMS))],
                    'GD': [str(int(meal['Delta'])) for i in range(len(df_meal_CGM.ZeroedCGMS))],
                    'cal': [str(int(meal['Energy (kcal)'])) for i in range(len(df_meal_CGM.ZeroedCGMS))],
                    'carb': [str(int(meal['Net Carbs (g)'])) for i in range(len(df_meal_CGM.ZeroedCGMS))],
                    'Food': [meal['Food Name'] for i in range(len(df_meal_CGM.ZeroedCGMS))]}
            source = ColumnDataSource(xydata)
            line = p.line('RespTime', 'zg', line_width=4, color='grey', alpha=0.05,
                            muted_color='#e82317', muted_alpha=0.9, legend_label=name_string[0], source=source)
            df_data_summary = df_data_summary.append({'Date': meal['Date'],
                                    'Time': meal['Time'],
                                    'Meal': meal['Food Name'],
                                    'Peak Glucose': meal['Peak'],
                                    'Glucose Delta': meal['Delta'],
                                    'Calories': meal['Energy (kcal)'],
                                    'Carbs': meal['Net Carbs (g)']},ignore_index=True)

        # show the results
        hour_one = 10800000/3
        response_hour = Span(location=hour_one,
                                    dimension='height', line_color='black',
                                    line_dash='dashed', line_width=3)
        p.add_layout(response_hour)

        hour_two = (10800000/3)*2
        response_hour_2 = Span(location=hour_two,
                                dimension='height', line_color='black',
                                line_dash='dashed', line_width=3)
        p.add_layout(response_hour_2)
        p.title.text = "Glucose Response"
        p.xgrid[0].grid_line_color=None
        p.ygrid[0].grid_line_alpha=0.5
        p.xaxis.axis_label = 'Time'
        p.yaxis.axis_label = 'mmol/dl'
        p.yaxis.ticker = [-100, -50, 0, 50, 100, 120]
        p.plot_width = 3200
        p.plot_height = 3100
        p.legend.click_policy="mute"
        temp_list = list(df_plot_data['Meal'])

        mid_box = BoxAnnotation(bottom=-100, top=40, fill_alpha=0.1, fill_color='green')
        high_box = BoxAnnotation(bottom=40, top=140, fill_alpha=0.1, fill_color='red')

        p.add_layout(mid_box)
        p.add_layout(high_box)

        p.add_layout(p.legend[0], 'left')
        show(p)
        df_data_summary.to_csv(self.output + os.path.sep + 'MealResponse.csv', index=False)
        print('just wait until I finish')

    # Methods to perform deeper correlational analysis
    def deep_analysis(self):
        for analysis in self.analysis:
            print("deep analysis", analysis)