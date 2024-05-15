from datetime import datetime

from Batch_CTABacktesting.BatchCTABacktesting import BatchCTABackTest
if __name__ == '__main__':
    bts = BatchCTABackTest()

    argumentlist = [
        # {"startDate": datetime(2022,8,8), "endDate": datetime(2023, 3, 10), "vt_symbol":"ag2304.SHFE"}
        {"startDate": datetime(2020, 6, 8), "endDate": datetime(2022, 12, 15), "vt_symbol": "sp9999.SHFE"}
        # {"startDate": datetime(2020, 6, 8), "endDate": datetime(2020, 11, 15), "vt_symbol": "ag2101.SHFE"}
        # {"startDate": datetime(2020, 6, 8), "endDate": datetime(2020, 11, 15), "vt_symbol": "lu2101.INE"}
        # {"startDate": datetime(2021, 11, 8), "endDate": datetime(2022, 4, 1), "vt_symbol": "lu2401.INE"}
    ]
    for argument in argumentlist:
        bts.runBatchTestExcecl(startDate = argument["startDate"],endDate = argument["endDate"],vt_symbol = argument["vt_symbol"])