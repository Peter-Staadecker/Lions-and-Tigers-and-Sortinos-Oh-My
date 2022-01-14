
# --------------------------------------------------------------------------------------------------------------------
# This program attempts to calculate the % up-market captures, the %-down market captures, the beta and the Sortino
# ratios for a list of US-traded stock tickers input by the user, and for a data time span selected by the user.
# The program uses metadata and price data from api.tiingo.com. A Tiingo API key is required and will not be shown
# when this code is displayed publicly. The user inputs his/her API key, a list of stocks of interest, including SPY
# as the first in the list. The user inputs the start and end dates for the data requests, a frequency (monthly,
# yearly, weekly, daily) as well as a minimum acceptable rate of return (aka min. target return).
# The program outputs the price data, the period-upon-period changes, and the final statistics (market capture, beta,
# Sortino) as separate worksheets in a single Excel file. For the price and price change worksheets, the rows are dates
# and the columns are the selected stocks. For the statistics (beta, up/down market captures and Sortino ratios)
# the rows are the selected stocks and the columnn headings are the ratios. The files are output to
# the same directory in which the program resides.

# The program was written as a Python learning exercise. It is not intended for stock trading,
# trading advice, or any other purpose. My definition of various ratios may not match other definitions,
# nor is the program in any way guaranteed to be error-free. Comments, corrections and suggestions are welcome.
#
#  --------------------------------------------------------------------------------------------------------------------

import pandas as pd
import numpy as np
from datetime import datetime
import copy
import io
import requests
import json
import xlsxwriter

# --------------------------------main-------------------------------------------------------------------------------

# --------------------------------user input here, modify as needed ------------------------------------

# apikey, url for stock meta data and for end-of day
apiKey: str = "<INSERT YOUR TIINGO API KEY HERE>"

# ticker list and description.
stockListInput = ["SPY", "ATO", "ED", "RY", "BNS", "TD", "WEC", "DGX", "JPM"]
listDescription: str = "test run"  # will be part of file name

# dates and data frequency
startDateStr: str = "2016-12-01"   # 1 extra price data point, because price growth loses one data point
endDateStr: str = "2021-12-01"
dataFreqStr: str = "monthly"  # weekly, monthly, annually, daily

# annualized minimum acceptable return (aka target) for Sortino ratio. Input as decimal, NOT as %
minAccRetAnnlzd: float = 0.005  # e.g. .005 is .5%

# -----------------------------------check input data and clean as necessary ---------------------------

if apiKey == "<INSERT YOUR TIINGO API KEY HERE>":
    print("You must obtain a valid api key from Tiingo and insert it into the program code.")
    exit()

# stocks must be uppercase, and instead of '.', Tiingo uses a '-'. E.g. BF.B becomes BF-B
stockList: list = []
for stocks in stockListInput:
    stocks = stocks.upper()
    stocks = stocks.replace('.', '-')
    stockList = stockList + [stocks]

# first stock must be SPY - the reference market
if stockList[0] != "SPY":
    print("Error. First stock must be SPY. Program ended.")
    exit()  # stop program

# --------------------------------------initialize misc. variables -----------------------------------
PeriodsInYr: float = 12  # for annualizing less-than-yearly data.  <---attention////

if dataFreqStr == "weekly":
    PeriodsInYr = 52
elif dataFreqStr == "monthly":
    PeriodsInYr = 12
elif dataFreqStr == "annually":
    PeriodsInYr = 1
elif dataFreqStr == "daily":
    PeriodsInYr = 253  # using an average
else:
    print("Error. Periods in year must be input as either 'weekly', 'monthly', 'annually', or 'daily'. Please correct.")
    exit()  # Program ends.

startDateReqDT: datetime = datetime.strptime(startDateStr, '%Y-%m-%d')
endDateReqDT: datetime = datetime.strptime(endDateStr, '%Y-%m-%d')
minAccRetInPeriod: float = (1 + minAccRetAnnlzd) ** (1/PeriodsInYr) - 1
headers = {'Content-Type': 'application/json'}
urlDaily: str = "https://api.tiingo.com/tiingo/daily/"

# prepare a dataframe to hold the results for all stocks. Columns are stock tickers, rows are successive trading dates
# data contents = adjusted closing prices
cols: list = ["date"] + stockList
priceMatrixDF = pd.DataFrame(columns=cols)
statsMatrixDF = pd.DataFrame(columns=stockList,
                             index=["beta", "std dev", "mkt up periods", "mkt dn periods", "cum chg up mkt",
                                                  "cum chg dn mkt", "cum chg up mkt annlzd", "cum chg dn mkt annlzd",
                                                  "cum chg up mkt %", "cum chg dn mkt %", "cum chg up mkt annlzd %",
                                                  "cum chg dn mkt annlzd %", "upside capture %", "dwnside capture %",
                                                  "sortino"])

# -----------------------------check stock tickers, stock meta data and stock history
errorsFound: bool = False
for stock in stockList:
    # get metadata
    stockUrl: str = urlDaily + stock + "?token=" + apiKey
    metaDataStr: str = requests.get(stockUrl, headers=headers).text

    if metaDataStr == '{"detail":"Not found."}':
        print("Error. Ticker ", stock, "not found in Tiingo.")
        errorsFound = True
        continue    # move on to next stock

    metaData: dict = json.loads(metaDataStr)
    stockName: str = metaData["name"]
    firstDateAvailStr: str = metaData["startDate"]
    lastDateAvailStr: str = metaData["endDate"]

    if firstDateAvailStr is None or lastDateAvailStr is None:
        print("Error: earlies and/or latest dates in meta data missing for ", stock)
        errorsFound = True
        continue  # jump to next stock

    firstDateAvail: datetime = datetime.strptime(firstDateAvailStr, '%Y-%m-%d')
    lastDateAvail: datetime = datetime.strptime(lastDateAvailStr, '%Y-%m-%d')

    if firstDateAvail > startDateReqDT or lastDateAvail < endDateReqDT:
        print("Error: data series shorter than requested for", stock, "Program ended.")
        errorsFound = True
        continue  # jump to next stock

    print("Metadata for ", stock, " is OK.")

if errorsFound:
    print("Program ending because of errors listed above")
    exit()

# -------------------------------------------get stock prices
for stock in stockList:
    print("Getting price data for ", stock)
    priceUrl: str = urlDaily + stock + "/prices?startDate=" + startDateStr + "&endDate=" + \
                    endDateStr + "&resampleFreq=" + dataFreqStr + "&token=" + apiKey + "&format=csv"
    dataStr = requests.get(priceUrl, headers=headers).text
    # convert dataStr to IO-like object as though from file
    dataIO = io.StringIO(dataStr)
    # read into a pandas dataframe
    singleStockPriceDF = pd.read_csv(dataIO, sep=",")
    # get trade dates from first stock, as well as adjusted close
    if stock == stockList[0]:
        priceMatrixDF[["date", stock]] = singleStockPriceDF[["date", "adjClose"]]
    else:
        # NB assumption all stocks trade on same dates - have not checked programmatically
        priceMatrixDF[[stock]] = singleStockPriceDF[["adjClose"]]

# --------------------strip away any rows with NaN values
priceMatrixDF = priceMatrixDF.dropna(axis=0)
# calculate increases in stock prices
priceChangeDF = copy.deepcopy(priceMatrixDF)
priceChangeDF[stockList] = 1 + priceMatrixDF[stockList].pct_change()
priceChangeDF = priceChangeDF.dropna(axis=0)

# ---------------calculate upmarket/downmarket capture for each stock
for stock in stockList:
    print("Calculating up/down market capture for ", stock)
    upPeriods: int = 0
    dnPeriods: int = 0
    # DUM - during up market; DDM - during down market
    cumChangeDUM: float = 1
    cumChangeDDM: float = 1

    for i in priceChangeDF.index:
        if priceChangeDF.loc[i, "SPY"] > 1:  # note that up/down periods are defined by SPY - the market proxy
            upPeriods = upPeriods + 1
            cumChangeDUM = cumChangeDUM * priceChangeDF.loc[i, stock]
        if priceChangeDF.loc[i, "SPY"] < 1:
            dnPeriods = dnPeriods + 1
            cumChangeDDM = cumChangeDDM * priceChangeDF.loc[i, stock]

    # summarize results for each stock the statsMatrixDF
    statsMatrixDF.loc["mkt dn periods", stock] = dnPeriods
    statsMatrixDF.loc["mkt up periods", stock] = upPeriods
    statsMatrixDF.loc["cum chg up mkt", stock] = cumChangeDUM
    statsMatrixDF.loc["cum chg dn mkt", stock] = cumChangeDDM
    statsMatrixDF.loc["cum chg up mkt %", stock] = (cumChangeDUM - 1) * 100
    statsMatrixDF.loc["cum chg dn mkt %", stock] = (cumChangeDDM - 1) * 100

    # annualized up and down market captures
    statsMatrixDF.loc["cum chg up mkt annlzd", stock] = float(cumChangeDUM ** (PeriodsInYr/upPeriods))
    statsMatrixDF.loc["cum chg dn mkt annlzd", stock] = float(cumChangeDDM ** (PeriodsInYr/dnPeriods))
    statsMatrixDF.loc["cum chg up mkt annlzd %", stock] = float((cumChangeDUM ** (PeriodsInYr/upPeriods)-1)*100)
    statsMatrixDF.loc["cum chg dn mkt annlzd %", stock] = float((cumChangeDDM ** (PeriodsInYr/dnPeriods)-1)*100)

    # compare other stocks to SPY, the market proxy.
    statsMatrixDF.loc["upside capture %", stock] = \
        float(100 * statsMatrixDF.loc["cum chg up mkt annlzd %", stock]
              / statsMatrixDF.loc["cum chg up mkt annlzd %", "SPY"])
    statsMatrixDF.loc["dwnside capture %", stock] = \
        float(100 * statsMatrixDF.loc["cum chg dn mkt annlzd %", stock]
              / statsMatrixDF.loc["cum chg dn mkt annlzd %", "SPY"])

# ------------------calculate beta of each stock with reference to SPY
# beta is covariance(stock growth, SPY growth)/(variance SPY growth)
# doesn't matter whether you use growth ratio or percentages
# To start, calculate variance of spy
mktVariance: float = np.cov(priceChangeDF[["SPY"]], priceChangeDF[["SPY"]], rowvar=False)[0, 0]
for stock in stockList:
    print("Calculating beta for ", stock)
    # the following numpy covariance function returns a 2x2 matrix. with the variance on the [0,0] and [1,1] elements
    # and the covariance between the 2 series on the [0,1] and [1,0] elements
    statsMatrixDF.loc["beta", stock] = np.cov(priceChangeDF[["SPY"]], priceChangeDF[[stock]], rowvar=False)[0, 1] \
                                      / mktVariance

# ------------------ calculate Sortino ratio =  (stock return - minimum acceptable return)/ downside std dev
# note 1. returns are % growth, not growth ratio
# note 2. downside std dev counts all periods both above and below target in the std dev denominator,
#   i.e. the zero values in the downside are not thrown away. For emphasis on this point see
#   e.g. http://www.redrockcapital.com/Sortino__A__Sharper__Ratio_Red_Rock_Capital.pdf
# note 3. I use a geometric average for average growth in calculating the numerator of the Sortino ratio.
#   Some may prefer an arithmetic ratio. Based on some quick tests the difference is likely minor.
# note 4. I use std. deviation for the population, not for a sample. Again the differences are likely minor.
# note 5. There are however, major differences in ratios depending on whether the data frequency is daily, weekly
#   monthly or yearly. As a result, it seems that the ratios (up/down market capture and Sortino) are more
#   useful for comparison between stocks when measured with the same data frequency, rather than as an absolute measure.
#   The beta ratio seems least influenced by frequency.
#
# prepare dataframe to hold calculation of returns, downside returns etc.
sortinoDF = pd.DataFrame(index=priceChangeDF.index, columns=["stock return", "downside return", "cumGrowth"])
for stock in stockList:
    CumGrowth: float = 1
    for i in priceChangeDF.index:
        CumGrowth = CumGrowth * priceChangeDF.loc[i, stock]
        sortinoDF.loc[i, "stock return"] = priceChangeDF.loc[i, stock] - 1  # in data period chosen
        sortinoDF.loc[i, "downside return"] = min(0, sortinoDF.loc[i, "stock return"] - minAccRetInPeriod)

    # now calculate summary for all periods for that stock
    CumStockReturn: float = CumGrowth - 1  # adjust for period if needed <-----------------------///////////////
    # note below that ** (PeriodsinYr/len(priceChangeDF.index)) is more accurate than ** (1/Number of Years)
    CumStockReturnAnnlzd: float = (CumGrowth ** (PeriodsInYr / len(priceChangeDF.index)))-1
    downsideStdDevPeriod: float = np.std(sortinoDF[['downside return']], axis=0)[0]
    downsideStdDevAnnlzd: float = downsideStdDevPeriod * (PeriodsInYr ** 0.5)  # <----////////adjust if needed
    # print(" cum st ret ",CumStockReturn, " annlzd ",CumStockReturnAnnlzd, "dwnside std dev ", \
    # downsideStdDevPeriod, " annlzd ",downsideStdDevAnnlzd)
    statsMatrixDF.loc["sortino", stock] = (CumStockReturnAnnlzd - minAccRetAnnlzd) / downsideStdDevAnnlzd
    if stock == "SPY":
        print("The raw data is from Tiingo. It is not intended for stock trading or trading advice. \n "
              "or any other purpose. My definition of calculated ratios may not match your definitions, \n"
              " nor is the program and output in any way guaranteed to be error-free.")
    print("For ", stock, "sortino ratio = ", statsMatrixDF.loc["sortino", stock])
    stdDevStockReturn: float = np.std(sortinoDF[['stock return']], axis=0)[0]
    stdDevStockReturnAnnlzd: float = stdDevStockReturn * (PeriodsInYr ** 0.5)
    statsMatrixDF.loc["std dev", stock] = stdDevStockReturnAnnlzd

# ------------------print and write results te Excel
dateTimeObj = datetime.now()
timestampStr = dateTimeObj.strftime("%d-%b-%y %H-%M")
fileSuffix: str = listDescription + " " + dataFreqStr + " data from " + startDateStr + " to " \
                  + endDateStr + ".xlsx"
text1 = fileSuffix + " as at " + timestampStr
text2 = "Price data is from api.tiingo.com. All other data is calculated by program. " \
        "The program is for Python programming training only, not for trading or stock advice or any other purpose."
fileName: str = "Sortino -" + fileSuffix

try:
    writer = pd.ExcelWriter(fileName, engine="xlsxwriter")

    statsMatrixTransposeDF = statsMatrixDF.transpose()
    statsMatrixTransposeDF.to_excel(writer, startrow=4, startcol=0, sheet_name='Calculated Ratios')
    worksheet = writer.sheets['Calculated Ratios']
    worksheet.write(0, 0, text1)
    worksheet.write(1, 0, text2)
    worksheet.set_row(5, 43)  # increase row height of grid title

    priceMatrixDF.to_excel(writer, startrow=4, startcol=0, sheet_name='Raw Price Data')
    worksheet = writer.sheets['Raw Price Data']
    worksheet.write(0, 0, text1)
    worksheet.write(1, 0, text2)

    priceChangeDF.to_excel(writer, startrow=4, startcol=0, sheet_name='Price Change')
    worksheet = writer.sheets['Price Change']
    worksheet.write(0, 0, text1)
    worksheet.write(1, 0, text2)
    worksheet.write(3, 0, "THESE ARE GROWTH RATIOS - NOT PERCENT")

    sortinoDF.to_excel(writer, startrow=4, startcol=0, sheet_name='Sortino Data Example for ' + stockList[-1])
    worksheet = writer.sheets['Sortino Data Example for ' + stockList[-1]]
    worksheet.write(0, 0, text1)
    worksheet.write(1, 0, text2)

    writer.save()

except IOError:
    print("Could not open file! Is it already/still open? Please close it, then rerun the program.")
    input("Please press enter to confirm you've seen this message.")
    exit()

print("The Excel file has been saved and is available for view in the same directory as the program.")
print("The file name is: ", fileName)
