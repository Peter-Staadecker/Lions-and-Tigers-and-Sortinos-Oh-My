# Lions-and-Tigers-and-Sortinos-Oh-My

This is a Python program to calculate the beta, up-market capture, down-market capture and Sortino ratios for user-selected stocks, over a user-selected time span, using a user-selected data frequency (yearly, monthly, weekly, daily). The eligible stocks are principally US-traded stocks. The program was written as a Python learning exercise and should not be relied on for any other purpose.

The user hard codes his/her inputs into the opening section of the Python program. The program takes its adjusted stock price data from https://api.tiingo.com/. The user must obtain an API key from Tiingo and hard code it into the opening section of the Python program.

The program saves its output as an Excel workbook in the same directory as the program. There are several worksheets in the workbook. The main worksheet is a grid showing the user-selected stock symbols (as rows) and the calculated ratios (as columns).

The program uses Python Pandas, so perhaps the title should have been Lions and Tigers and Pandas, Oh My. 

Disclaimers: no animals were harmed in the making of this program. Nor is the program fit for stock trading, trading advice or any other purpose. Comments, corrections and suggestions are welcome. NB If the Tiingo APIs or the underlying Tiingo data structures change, this program will no longer function correctly.
