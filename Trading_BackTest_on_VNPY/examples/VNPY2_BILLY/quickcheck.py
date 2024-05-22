from vnpy.trader.database import database_manager
from datetime import datetime, timedelta
def sort_list(db_tri_stop_order_data_list):

    return sorted(db_tri_stop_order_data_list, key=lambda x: (x.datetime, x.stop_orderid.split(".")[1] if x.datetime == x.datetime else 0), reverse=True)

if __name__ == "__main__":
    dbstop_orders = database_manager.load_triggered_stop_order_data("j4", start = datetime(2001,10,10), end = datetime(2100,10,10))
    dbstop_orders = sort_list(dbstop_orders)
    for ddstop in dbstop_orders:
        print(f"{ddstop.datetime} and {ddstop.stop_orderid}" )

