import type { Quote } from '../types';

export interface ExpiryInfo {
  month: string; // 'Mar', 'Jun', 'Sep', 'Dec'
  monthIndex: number; // 0=Mar, 1=Jun, 2=Sep, 3=Dec
  year: number;
  fullDate: Date; // For sorting
}

export interface ContractInfo {
  instrument: string;
  product: 'SA3' | 'ER3';
  expiry: ExpiryInfo;
}

export interface ContractPair {
  sa3: string;
  er3: string;
  expiry: ExpiryInfo;
}

export interface OutrightRow {
  pair: ContractPair;
  sa3Value: number | null;
  er3Value: number | null;
  difference: number | null;
  sa3Change: number | null;
  er3Change: number | null;
}

export interface SpreadRow {
  name: string;
  legs: ContractPair[];
  sa3Value: number | null;
  er3Value: number | null;
  difference: number | null;
  type: 'spread' | 'fly';
}

const QUARTERS = ['Mar', 'Jun', 'Sep', 'Dec'];
const QUARTER_INDICES: Record<string, number> = {
  'Mar': 0, 'Jun': 1, 'Sep': 2, 'Dec': 3
};

export function parseExpiry(instrument: string): ExpiryInfo | null {
  // Match formats like "SA3 Jun26" or "ER3 JUN26"
  const match = instrument.match(/^([A-Z]+\d+)\s+([A-Z]{3})(\d{2})$/i);
  if (!match) return null;

  const monthMap: Record<string, string> = {
    'jan': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'apr': 'Apr', 'may': 'May', 'jun': 'Jun',
    'jul': 'Jul', 'aug': 'Aug', 'sep': 'Sep', 'oct': 'Oct', 'nov': 'Nov', 'dec': 'Dec'
  };

  const monthName = monthMap[match[2].toLowerCase()];
  if (!monthName) return null;

  const year = 2000 + parseInt(match[3], 10);
  const monthIndex = QUARTER_INDICES[monthName];

  // Create a date for proper chronological sorting
  // Use the last day of the quarter month
  const monthNum = (monthIndex + 1) * 3; // Mar=3, Jun=6, Sep=9, Dec=12
  const fullDate = new Date(year, monthNum, 0); // Day 0 = last day of previous month

  return {
    month: monthName,
    monthIndex,
    year,
    fullDate,
  };
}

export function getProduct(instrument: string): 'SA3' | 'ER3' | null {
  if (instrument.startsWith('SA3')) return 'SA3';
  if (instrument.startsWith('ER3')) return 'ER3';
  return null;
}

export function parseAllContracts(contracts: { SA3: string[]; ER3: string[] }): ContractInfo[] {
  const all: ContractInfo[] = [];

  contracts.SA3.forEach(instrument => {
    const expiry = parseExpiry(instrument);
    if (expiry) {
      all.push({ instrument, product: 'SA3', expiry });
    }
  });

  contracts.ER3.forEach(instrument => {
    const expiry = parseExpiry(instrument);
    if (expiry) {
      all.push({ instrument, product: 'ER3', expiry });
    }
  });

  // Sort chronologically by expiry date
  all.sort((a, b) => a.expiry.fullDate.getTime() - b.expiry.fullDate.getTime());

  return all;
}

export function buildContractPairs(contracts: { SA3: string[]; ER3: string[] }): ContractPair[] {
  const allContracts = parseAllContracts(contracts);

  // Group by expiry date
  const byExpiry = new Map<string, { sa3?: string; er3?: string; expiryInfo?: ExpiryInfo }>();

  allContracts.forEach(contract => {
    const key = `${contract.expiry.year}-${contract.expiry.monthIndex}`;
    const group = byExpiry.get(key) || { expiryInfo: contract.expiry };
    if (contract.product === 'SA3') group.sa3 = contract.instrument;
    else group.er3 = contract.instrument;
    byExpiry.set(key, group);
  });

  // Build pairs only where both SA3 and ER3 exist
  const pairs: ContractPair[] = [];
  for (const group of byExpiry.values()) {
    if (group.sa3 && group.er3 && group.expiryInfo) {
      pairs.push({
        sa3: group.sa3,
        er3: group.er3,
        expiry: group.expiryInfo,
      });
    }
  }

  // Sort chronologically
  pairs.sort((a, b) => a.expiry.fullDate.getTime() - b.expiry.fullDate.getTime());

  return pairs;
}

export function getOutrightValue(instrument: string, quotes: Record<string, Quote>): number | null {
  const quote = quotes[instrument];
  if (!quote) return null;
  return quote.mid ?? quote.price ?? quote.last ?? null;
}

export function getOutrightChange(instrument: string, quotes: Record<string, Quote>): number | null {
  const quote = quotes[instrument];
  if (!quote) return null;
  return quote.net_change ?? null;
}

export function buildOutrightRows(pairs: ContractPair[], quotes: Record<string, Quote>): OutrightRow[] {
  return pairs.map(pair => {
    const sa3Value = getOutrightValue(pair.sa3, quotes);
    const er3Value = getOutrightValue(pair.er3, quotes);
    const difference = sa3Value !== null && er3Value !== null ? sa3Value - er3Value : null;

    return {
      pair,
      sa3Value,
      er3Value,
      difference,
      sa3Change: getOutrightChange(pair.sa3, quotes),
      er3Change: getOutrightChange(pair.er3, quotes),
    };
  });
}

function isConsecutiveQuarter(expiry1: ExpiryInfo, expiry2: ExpiryInfo): boolean {
  // Check if expiry2 is exactly 3 months after expiry1
  if (expiry1.monthIndex === 3) { // Dec
    return expiry2.monthIndex === 0 && expiry2.year === expiry1.year + 1; // Mar next year
  } else {
    return (
      expiry2.year === expiry1.year &&
      expiry2.monthIndex === expiry1.monthIndex + 1
    );
  }
}

export function build3MSRows(pairs: ContractPair[], quotes: Record<string, Quote>): SpreadRow[] {
  const rows: SpreadRow[] = [];

  // Only create spreads between consecutive quarterly contracts
  for (let i = 0; i < pairs.length - 1; i++) {
    const pair1 = pairs[i];
    const pair2 = pairs[i + 1];

    // Validate consecutive quarters
    if (!isConsecutiveQuarter(pair1.expiry, pair2.expiry)) {
      continue;
    }

    const sa3_1 = getOutrightValue(pair1.sa3, quotes);
    const sa3_2 = getOutrightValue(pair2.sa3, quotes);
    const er3_1 = getOutrightValue(pair1.er3, quotes);
    const er3_2 = getOutrightValue(pair2.er3, quotes);

    // Only create if all legs exist
    if (sa3_1 === null || sa3_2 === null || er3_1 === null || er3_2 === null) {
      continue;
    }

    const sa3Value = sa3_1 - sa3_2;
    const er3Value = er3_1 - er3_2;
    const difference = sa3Value - er3Value;

    const expiryStr1 = `${pair1.expiry.month}${pair1.expiry.year}`;
    const expiryStr2 = `${pair2.expiry.month}${pair2.expiry.year}`;

    rows.push({
      name: `${expiryStr1}/${expiryStr2}`,
      legs: [pair1, pair2],
      sa3Value,
      er3Value,
      difference,
      type: 'spread',
    });
  }

  return rows;
}

export function build3MFRows(pairs: ContractPair[], quotes: Record<string, Quote>): SpreadRow[] {
  const rows: SpreadRow[] = [];

  // Only create flies with three consecutive quarterly contracts
  for (let i = 0; i < pairs.length - 2; i++) {
    const pair1 = pairs[i];
    const pair2 = pairs[i + 1];
    const pair3 = pairs[i + 2];

    // Validate consecutive quarters
    if (!isConsecutiveQuarter(pair1.expiry, pair2.expiry)) {
      continue;
    }
    if (!isConsecutiveQuarter(pair2.expiry, pair3.expiry)) {
      continue;
    }

    const sa3_1 = getOutrightValue(pair1.sa3, quotes);
    const sa3_2 = getOutrightValue(pair2.sa3, quotes);
    const sa3_3 = getOutrightValue(pair3.sa3, quotes);
    const er3_1 = getOutrightValue(pair1.er3, quotes);
    const er3_2 = getOutrightValue(pair2.er3, quotes);
    const er3_3 = getOutrightValue(pair3.er3, quotes);

    // Only create if all legs exist
    if (
      sa3_1 === null || sa3_2 === null || sa3_3 === null ||
      er3_1 === null || er3_2 === null || er3_3 === null
    ) {
      continue;
    }

    const sa3Value = sa3_1 - 2 * sa3_2 + sa3_3;
    const er3Value = er3_1 - 2 * er3_2 + er3_3;
    const difference = sa3Value - er3Value;

    const expiryStr1 = `${pair1.expiry.month}${pair1.expiry.year}`;
    const expiryStr2 = `${pair2.expiry.month}${pair2.expiry.year}`;
    const expiryStr3 = `${pair3.expiry.month}${pair3.expiry.year}`;

    rows.push({
      name: `${expiryStr1}/${expiryStr2}/${expiryStr3}`,
      legs: [pair1, pair2, pair3],
      sa3Value,
      er3Value,
      difference,
      type: 'fly',
    });
  }

  return rows;
}
