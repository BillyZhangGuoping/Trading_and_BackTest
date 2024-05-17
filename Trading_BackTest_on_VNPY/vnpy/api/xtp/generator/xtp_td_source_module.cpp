.def("queryOrderByXTPID", &TdApi::queryOrderByXTPID)
.def("queryOrders", &TdApi::queryOrders)
.def("queryTradesByXTPID", &TdApi::queryTradesByXTPID)
.def("queryTrades", &TdApi::queryTrades)
.def("queryPosition", &TdApi::queryPosition)
.def("queryAsset", &TdApi::queryAsset)
.def("queryStructuredFund", &TdApi::queryStructuredFund)
.def("queryFundTransfer", &TdApi::queryFundTransfer)
.def("queryETF", &TdApi::queryETF)
.def("queryETFTickerBasket", &TdApi::queryETFTickerBasket)
.def("queryIPOInfoList", &TdApi::queryIPOInfoList)
.def("queryIPOQuotaInfo", &TdApi::queryIPOQuotaInfo)
.def("queryOptionAuctionInfo", &TdApi::queryOptionAuctionInfo)
.def("queryCreditCashRepayInfo", &TdApi::queryCreditCashRepayInfo)
.def("queryCreditFundInfo", &TdApi::queryCreditFundInfo)
.def("queryCreditDebtInfo", &TdApi::queryCreditDebtInfo)
.def("queryCreditTickerDebtInfo", &TdApi::queryCreditTickerDebtInfo)
.def("queryCreditAssetDebtInfo", &TdApi::queryCreditAssetDebtInfo)
.def("queryCreditTickerAssignInfo", &TdApi::queryCreditTickerAssignInfo)
.def("queryCreditExcessStock", &TdApi::queryCreditExcessStock)

.def("onDisconnected", &TdApi::onDisconnected)
.def("onError", &TdApi::onError)
.def("onOrderEvent", &TdApi::onOrderEvent)
.def("onTradeEvent", &TdApi::onTradeEvent)
.def("onCancelOrderError", &TdApi::onCancelOrderError)
.def("onQueryOrder", &TdApi::onQueryOrder)
.def("onQueryTrade", &TdApi::onQueryTrade)
.def("onQueryPosition", &TdApi::onQueryPosition)
.def("onQueryAsset", &TdApi::onQueryAsset)
.def("onQueryStructuredFund", &TdApi::onQueryStructuredFund)
.def("onQueryFundTransfer", &TdApi::onQueryFundTransfer)
.def("onFundTransfer", &TdApi::onFundTransfer)
.def("onQueryETF", &TdApi::onQueryETF)
.def("onQueryETFBasket", &TdApi::onQueryETFBasket)
.def("onQueryIPOInfoList", &TdApi::onQueryIPOInfoList)
.def("onQueryIPOQuotaInfo", &TdApi::onQueryIPOQuotaInfo)
.def("onQueryOptionAuctionInfo", &TdApi::onQueryOptionAuctionInfo)
.def("onCreditCashRepay", &TdApi::onCreditCashRepay)
.def("onQueryCreditCashRepayInfo", &TdApi::onQueryCreditCashRepayInfo)
.def("onQueryCreditFundInfo", &TdApi::onQueryCreditFundInfo)
.def("onQueryCreditDebtInfo", &TdApi::onQueryCreditDebtInfo)
.def("onQueryCreditTickerDebtInfo", &TdApi::onQueryCreditTickerDebtInfo)
.def("onQueryCreditAssetDebtInfo", &TdApi::onQueryCreditAssetDebtInfo)
.def("onQueryCreditTickerAssignInfo", &TdApi::onQueryCreditTickerAssignInfo)
.def("onQueryCreditExcessStock", &TdApi::onQueryCreditExcessStock)
;