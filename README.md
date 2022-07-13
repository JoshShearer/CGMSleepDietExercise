# CGM Data Processing - Sleep, Diet, Exercise
This script will take in and process data from the following sources

```yaml
xDrip+ => Continuous Glucose Monitoring Data
Oura => Sleep Data
Cronometer> = Food Intake and suppliment consumption
Garmin => Exercise and training data
```

## Setup 

To run the bot, open the command line in the cloned repo directory and install the requirements using pip with the following command:
```bash
pip install -r requirements.txt
```

Next, you need to fill out the config.yaml file. Most of this is self-explanatory but if you need explanations please see the end of this README.

```yaml
dataFiles:
 CGMData: C:\xdrip\data.csv      #required
 ExData: C:\garmin\data.csv     #optional
sleepData: C:\oura\data.csv        #optional
 mealData: C:\crono\data.csv      #required

#date range for the CGM processing window.  Allows downloading all data instead of matching window.
# must be in the form of Month/Day/Year
dateRange:
 initialDay: 07/07/2020 #required
 finalDay: 09/11/2020   #required

#This will save all response graphs and data
dataAnalysis:
 calCorrection: True  #In the event that your xDrip does not correct readings after a spot calibration
 loadMealResp: True    #Glucose Response Graphs will be saved to the outputFileDirectory.  They can also be launched in the browser.

 sleepCorr: True       #Sleep Data will be used to show potential correlations with glucose response
 exerciseCorr: True    #Exercise Data will be used to show potential correlations with glucose response and added to meal response graphs
 biometricCorr: True   #biometricMetrics from cronometer will be used to show potential correlations with glucose response
 matplotlib: False     #A step response via matplotlib for each meal above 5 carbs
 bokeh: False           #A step response via BOKEH for each meal above 5 carbs
 heat: False            #A heat map covering the entire duration window
 multiplot: True       #A single plot with all step responses shown.

adjustments:
  calWindow: 5    #If you are adjusting the data for calibration, this will adjust and smooth values over this number of hours.
  responseTime: 3 #window of time from meal start to measure glucose response      

#This will save all response graphs and data
outputFileDirectory: C:\CGMOutputData
```


## Execute

To run the bot, run the following in the command line:
```
python3 main.py
```
## Sample Outputs

matplotlib (Step Response for each meal)
bokeh (Step Response for each meal)
heat (Heatmap of all meals over available data)
multiplot (Single plot with all meal step responses over teh available data)