export const formatCurrency = (amount, currency = 'USD') => {
	// For very small amounts, show more decimal places
	const value = amount || 0;
	const currencyOptions = currency === 'PLN' 
		? { style: 'currency', currency: 'PLN' }
		: { style: 'currency', currency: 'USD' };
		
	if (value > 0 && value < 0.01 && currency === 'USD') {
		return new Intl.NumberFormat('en-US', {
			...currencyOptions,
			minimumFractionDigits: 6,
			maximumFractionDigits: 6
		}).format(value);
	}
	
	return new Intl.NumberFormat(currency === 'PLN' ? 'pl-PL' : 'en-US', currencyOptions).format(value);
};

export const formatDualCurrency = (usdAmount, plnAmount) => {
	// Format as "$X.XX (Y.YY zł)"
	if (plnAmount !== undefined && plnAmount !== null) {
		return `${formatCurrency(usdAmount)} (${formatCurrency(plnAmount, 'PLN')})`;
	}
	// Fallback to USD only if PLN not available
	return formatCurrency(usdAmount);
};

export const formatNumber = (number) => {
	return new Intl.NumberFormat('en-US').format(number || 0);
};

export const formatPercentage = (value) => {
	return new Intl.NumberFormat('en-US', {
		style: 'percent',
		minimumFractionDigits: 1,
		maximumFractionDigits: 1
	}).format(value);
};