export type HouseholdSummary = {
  householdId: string;
  householdName: string;
  segment: string;
  aum: number;
  nnm: number;
  ncf: number;
  riskProfile: string;
  nextBestAction: string;
};

export type AccountSummary = {
  accountId: string;
  accountType: string;
  accountValue: number;
  managed: boolean;
  productExposure: string;
};

export type TransactionSummary = {
  transactionId: string;
  tradeDate: string;
  settlementDate: string;
  buySellFlag: "Buy" | "Sell";
  quantity: number;
  principalAmount: number;
  revenueAmount: number;
  productCategory: string;
};

export type CrmActivity = {
  activityId: string;
  activityType: string;
  activityDate: string;
  subject: string;
  outcome: string;
};

export type Advisor360Payload = {
  advisorId: string;
  advisorName: string;
  market: string;
  agpStatus: "On Track" | "At Risk" | "Off Track" | "Not AGP";
  revenueYtd: number;
  aum: number;
  nnm: number;
  ncf: number;
  households: HouseholdSummary[];
  accounts: AccountSummary[];
  transactions: TransactionSummary[];
  crmActivities: CrmActivity[];
};
