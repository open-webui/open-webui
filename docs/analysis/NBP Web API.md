# # NBP Web API
# Currency exchange rates and gold prices in the XML and JSON formats
The **api.nbp.pl** service operates a public Web ~API~ enabling ~HTTP~ clients to make enquiries on the following datasets published by the NBP.PL service:
1 ~[current and historic exchange rates of foreign currencies](https://api.nbp.pl/en.html#kursyWalut)~:
	* table A of middle exchange rates of foreign currencies,
	* table B of middle exchange rates of foreign currencies,
	* table C of buy and sell prices of foreign currencies;
2 ~[current and historic prices of gold calculated at NBP](https://api.nbp.pl/en.html#cenyZlota)~.

⠀Communication with the service based on parametrized HTTP GET requests send to the **https://api.nbp.pl/api/** address.
* ~[General information](https://api.nbp.pl/en.html#info)~
* ~[Description of API functions concerning currency exchange rates](https://api.nbp.pl/en.html#kursyWalut)~
  * ~[Exchange rate query parameters](https://api.nbp.pl/en.html#kursyParams)~
  * ~[Queries for complete tables](https://api.nbp.pl/en.html#kursyFull)~
  * ~[Queries for particular currency](https://api.nbp.pl/en.html#kursySingle)~
  * ~[Description of response parameters for exchange rate queries](https://api.nbp.pl/en.html#kursyOdp)~
* ~[Description of API functions concerning queries for gold prices](https://api.nbp.pl/en.html#cenyZlota)~
  * ~[Gold price query parameters](https://api.nbp.pl/en.html#zlotoParams)~
  * ~[Queries for gold prices](https://api.nbp.pl/en.html#zlotoFull)~
  * ~[Description of response parameters for gold price queries](https://api.nbp.pl/en.html#zlotoOdp)~
* ~[Query examples](https://api.nbp.pl/en.html#przyklady)~
* ~[Error messages](https://api.nbp.pl/en.html#errors)~

⠀User manual
**Important API Update: Transition to HTTPS Only**
Effective August 1, 2025, all API communications must be conducted over HTTPS.
The HTTP protocol will no longer be supported for accessing our API services.
This change is part of our ongoing commitment to enhancing security and protecting your data during transmission.

**Action Required** 
To ensure uninterrupted access to our API services starting August 1, 2025, please update your integration to use HTTPS endpoints.
Thank you for your understanding and cooperation as we make this important upgrade to enhance the security of our services.
### General Information
Service reply is returned in the ~JSON~ or ~XML~ format, depending on client requirements. The reply format may be indicated in two ways – with an query parameter ?format or with a HTTP Accept header:
* JSON format: Accept: application/json header or ?format=json parameter
* XML format: Accept: application/xml header or ?format=xml parameter

⠀If the format has not been determined, JSON is returned.
Historic data are available respectively:
* for currency exchange rates – since 2 January 2002,
* for gold prices – since 2 January 2013.

⠀and a single enquiry cannot cover a period longer than 93 days.
The time frame for enquiry results may be determined in one of the following ways:
* current data – the last released piece of data at the moment of making the enquiry,
* data published today – the value published on the given day,
* a series of data from the last N quotations,
* data for a particular date of publication,
* a series of data from a predetermined time bracket.

⠀Description of API functions concerning currency exchange rates
The data for currency exchange rates are made available in two ways:
* as a complete table of exchange rates (or a series of such tables) of a determined type,
* as an exchange rate (or a series of exchange rates) of a particular currency for a determined table type and currency symbol.

⠀**Exchange rate query parameters**
* {table} – table type (A, B, or C)
* {code} – a three- letter ~[currency code](https://www.currency-iso.org/en/home/tables/table-a1.html)~ (~[ISO 4217](https://en.wikipedia.org/wiki/ISO_4217)~ standard)
* {topCount} – a number determining the maximum size of the returned data series
* {date}, {startDate}, {endDate} – a date in the YYYY-MM-DD format (~[ISO 8601](https://en.wikipedia.org/wiki/ISO_8601)~ standard)

⠀**Queries for complete tables**
Templates of enquiries about complete tables of currency exchange rates
* Current table of exchange rates of type {table} https://api.nbp.pl/api/exchangerates/tables/{table}/
* Series of latest {topCount} tables of exchange rates of type {table} https://api.nbp.pl/api/exchangerates/tables/{table}/last/{topCount}/
* Exchange rate table of type {table} published today (or lack of data) https://api.nbp.pl/api/exchangerates/tables/{table}/today/
* Exchange rate table of type {table} published on {date} (or lack of data) https://api.nbp.pl/api/exchangerates/tables/{table}/{date}/
* Series of exchange rate tables of type {table} published from {startDate} to {endDate} (or lack of data) https://api.nbp.pl/api/exchangerates/tables/{table}/{startDate}/{endDate}/

⠀**Queries for particular currency**
Templates of enquiries about a particular currency exchange rate
* Current exchange rate {code} from the exchange rate table of type {table} https://api.nbp.pl/api/exchangerates/rates/{table}/{code}/
* Series of latest {topCount} exchange rates of currency {code} from the exchange rate table of type {table} https://api.nbp.pl/api/exchangerates/rates/{table}/{code}/last/{topCount}/
* Exchange rate of currency {code} from the exchange rate table of type {table} published today (or lack of data) https://api.nbp.pl/api/exchangerates/rates/{table}/{code}/today/
* Exchange rate of currency {code} from the exchange rate table of type {table} published on {date} (or lack of data) https://api.nbp.pl/api/exchangerates/rates/{table}/code}/{date}/
* Exchange rate of currency {code} from the exchange rate table of type {table} published from {startDate} to {endDate} (or lack of data) https://api.nbp.pl/api/exchangerates/rates/{table}/{code}/{startDate}/{endDate}/

⠀**Description of response parameters for exchange rate queries**
* Table – table type
* No – table number
* TradingDate – trading date (for table C only)
* EffectiveDate – publication date
* Rates – a list of exchange rates of particular currencies in the table
* Country – country name
* Symbol – currency symbol (numerical, concerns historic exchange rates)
* Currency – currency name
* Code – currency code
* Bid – calculated currency buy exchange rate (concerns table C) (for table C only)
* Ask – calculated currency sell exchange rate (concerns table C) ()
* Mid – calculated currency average exchange rate (for tables A and B)

⠀Description of API functions concerning queries for gold prices
**Gold price query parameters**
* {topCount} – a number determining the maximum size of returned data series
* {date}, {startDate}, {endDate} – a date in the YYYY-MM-DD format (~[ISO 8601](https://en.wikipedia.org/wiki/ISO_8601)~ standard)

⠀**Queries for gold prices**
* Current gold price https://api.nbp.pl/api/cenyzlota
* Series of latest {topCount} gold price quotations https://api.nbp.pl/api/cenyzlota/last/{topCount}
* Price of gold published today (or lack of data) https://api.nbp.pl/api/cenyzlota/today
* Price of gold published on {date} (or lack of data) https://api.nbp.pl/api/cenyzlota/{date}
* Series of gold prices published from {startDate} to {endDate} (or lack of data) https://api.nbp.pl/api/cenyzlota/{startDate}/{endDate}

⠀**Description of response parameters for gold price queries**
* Date – publication date
* Code – the price of 1g of gold (of 1000 millesimal fineness) calculated at NBP

⠀Query examples
**Currency exchange rates**
* Current average CHF exchange rate ~[https://api.nbp.pl/api/exchangerates/rates/a/chf/](https://api.nbp.pl/api/exchangerates/rates/a/chf/)~
* Quotation of USD buy and sell exchange rate published todayIf the current table has not been published yet, the 404 error code is returned ~[https://api.nbp.pl/api/exchangerates/rates/c/usd/today/](https://api.nbp.pl/api/exchangerates/rates/c/usd/today/)~
* Quotation of USD buy and sell exchange rate of 2016-04-04 in the JSON format ~[https://api.nbp.pl/api/exchangerates/rates/c/usd/2016-04-04/?format=json](https://api.nbp.pl/api/exchangerates/rates/c/usd/2016-04-04/?format=json)~
* Current table of type A of average exchange rates of foreign currencies ~[https://api.nbp.pl/api/exchangerates/tables/a/](https://api.nbp.pl/api/exchangerates/tables/a/)~
* Table of type A published todayIf today’s table has not been published yet, the 404 error code is returned ~[https://api.nbp.pl/api/exchangerates/tables/a/today/](https://api.nbp.pl/api/exchangerates/tables/a/today/)~
* Series of the last 10 quotations of GBP average exchange rate in the JSON ~[https://api.nbp.pl/api/exchangerates/rates/a/gbp/last/10/?format=json](https://api.nbp.pl/api/exchangerates/rates/a/gbp/last/10/?format=json)~
* Series of the last 10 quotations of USD buy and sell exchange rates in the XML format ~[https://api.nbp.pl/api/exchangerates/rates/c/usd/last/10/?format=xml](https://api.nbp.pl/api/exchangerates/rates/c/usd/last/10/?format=xml)~
* Series of GBP average exchange rates from 2012-01-01 to 2012-01-31 ~[https://api.nbp.pl/api/exchangerates/rates/a/gbp/2012-01-01/2012-01-31/](https://api.nbp.pl/api/exchangerates/rates/a/gbp/2012-01-01/2012-01-31/)~
* GBP average exchange rate on 2012-01-02 ~[https://api.nbp.pl/api/exchangerates/rates/a/gbp/2012-01-02/](https://api.nbp.pl/api/exchangerates/rates/a/gbp/2012-01-02/)~
* Series of last 5 tables of type A of average exchange rates of foreign currencies ~[https://api.nbp.pl/api/exchangerates/tables/a/last/5/](https://api.nbp.pl/api/exchangerates/tables/a/last/5/)~
* Series of tables of type A from 2012-01-01 to 2012-01-31 ~[https://api.nbp.pl/api/exchangerates/tables/a/2012-01-01/2012-01-31/](https://api.nbp.pl/api/exchangerates/tables/a/2012-01-01/2012-01-31/)~
* Table B as of 2016-03-30 ~[https://api.nbp.pl/api/exchangerates/tables/b/2016-03-30/](https://api.nbp.pl/api/exchangerates/tables/b/2016-03-30/)~

⠀**Gold prices**
* Current gold price ~[https://api.nbp.pl/api/cenyzlota/](https://api.nbp.pl/api/cenyzlota/)~
* Series of last 30 quotations of gold prices in the JSON format ~[https://api.nbp.pl/api/cenyzlota/last/30/?format=json](https://api.nbp.pl/api/cenyzlota/last/30/?format=json)~
* Gold price published today (or lack of data) ~[https://api.nbp.pl/api/cenyzlota/today/](https://api.nbp.pl/api/cenyzlota/today/)~
* Gold price published on 2013-01-02 ~[https://api.nbp.pl/api/cenyzlota/2013-01-02/](https://api.nbp.pl/api/cenyzlota/2013-01-02/)~
* Series of gold prices published from 2013-01-01 to 2013-01-31 ~[https://api.nbp.pl/api/cenyzlota/2013-01-01/2013-01-31/](https://api.nbp.pl/api/cenyzlota/2013-01-01/2013-01-31/)~

⠀Error messages
In the case of lack of data for a correctly determined time interval, 404 Not Found message is returned
In the case of incorrectly formulated enquiries, the service returns 400 Bad Request message
In the case of an enquiry/query exceeding the returned data size limit, the service returns the message 400 Bad Request - Limit exceeded
