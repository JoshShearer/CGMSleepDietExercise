# CGM Data Processing - Sleep, Diet, Exercise
This script will take in and process data from the following sources

```yaml
xDrip+      => Continuous Glucose Monitoring Data
Oura        => Sleep Data
Cronometer  => Food Intake and supplement consumption.  Biometric Data
Garmin      => Exercise and training data
```

## Setup 

To run the bot, open the command line in the cloned repo directory and install the requirements using pip with the following command:
```bash
pip install -r requirements.txt
```

Next, you need to fill out the config.yaml file. Most of this is self-explanatory but if you need explanations please see the end of this README.

```yaml


#directory of file including filename.  All files must be in .csv format
dataFiles:
 CGMData: C:\xdrip\data.csv      #required
 ExData: C:\garmin\data.csv    #optional
 sleepData: C:\oura\data.csv        #optional
 mealData: C:\crono\data.csv      #required
 BioData: H:\crono\data.csv     # optional 
#date range for the CGM processing window.  Allows downloading all data instead of matching window.
# must be in the form of Month/Day/Year
dateRange:
 initialDay: 07/07/2020 11:30 #required
 finalDay: 09/11/2020 08:45 #required

#This will save all response graphs and data
dataAnalysis:
 calCorrection: False  # In the event that your xDrip does not correct readings after a spot calibration
 loadMealResp: True    # Glucose Response Graphs will be saved to the outputFileDirectory.  They can also be launched in the browser.

 sleepCorr: True       # Sleep Data will be used to show potential correlations with glucose response
 exerciseCorr: True    # Exercise Data will be used to show potential correlations with glucose response and added to meal response graphs
 biometricCorr: True   # biometricMetrics from cronometer will be used to show potential correlations with glucose response
 matplotlib: False     # A step response via matplotlib for each meal above 5 carbs
 bokeh: True           # A step response via BOKEH for each meal above 5 carbs
 heat: True            # A heat map covering the entire duration window
 multiplot: True       # A single plot with all step responses shown.
 biometricCorr: True   # Will produce plots showing step responses for biometrics shown below.  Must match output
 supplementCorr: True  # Will produce plots showing step resonses for Supplements of interest shown below. String must match output

Biometrics:
  - Blood Pressure    #must match string found in biometrics.csv

Supplements:
  - creatine         #must match string found in servings/meal data

adjustments:
  calWindow: 5    # If you are adjusting the data for calibration, this will adjust and smooth values over this number of hours minutes and seconds.
  responseTime: 3 # window of time from meal start to measure glucose response   
  minCarbs: 5     # Grams of carbs threshhold for producing step response of food/meal  

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
![matplot](https://user-images.githubusercontent.com/50993714/178624101-c92fcc64-ad0a-4399-9c49-bba796ac2473.png)
bokeh (Step Response for each meal)
![MealStep](https://user-images.githubusercontent.com/50993714/180931631-09ddf523-1f43-461b-8708-9a37f7d38d83.png)
bokeh (Step Response for each workout)
![WorkoutStep](https://user-images.githubusercontent.com/50993714/180931638-0a616ea3-4fe1-46d2-af90-ee3a035013d3.png)
bokeh (Daily Overview/Summmary)
![DayOverview](https://user-images.githubusercontent.com/50993714/180931650-b2577054-e6b9-47ed-afbf-c30217590744.png)
heat (Heatmap of all meals over available data)
![bokeh_heat_view](https://user-images.githubusercontent.com/50993714/178624613-608b37d9-920c-4634-a6e4-733239b1069d.png)
multiplot (Single plot with all meal step responses over teh available data)
![bokeh_multi](https://user-images.githubusercontent.com/50993714/178624096-f99da1e8-b0d4-4e4f-898f-4353e814de38.png)