export type TargetType = 'Domain' | 'IP' | 'URL' | 'CIDR' | 'Host';

export type TargetStatus = 'Active' | 'Pending' | 'Paused' | 'Complete' | 'Error';

export type Target = {
	id: string;
	name: string;
	type: TargetType;
	value: string;
	status: TargetStatus;
	lastScan: string | null;
	description: string;
};

export type NewTargetInput = {
	name: string;
	type: TargetType;
	value: string;
	description: string;
};
