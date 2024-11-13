import { SuiClient } from '@mysten/sui/client';
import { Ed25519Keypair } from '@mysten/sui/keypairs/ed25519';
import {
	generateNonce,
	generateRandomness,
	getExtendedEphemeralPublicKey,
	getZkLoginSignature,
	jwtToAddress
} from '@mysten/zklogin';

const LOCAL_STORAGE_SALT = 'ZKLOGIN-SALT';
// const LOCAL_STORAGE_NONCE = 'ZKLOGIN'-NONCE';
const LOCAL_STORAGE_SECRET_KEY = 'ZKLOGIN-SECRET_KEY';
const LOCAL_STORAGE_RANDOMNESS = 'ZKLOGIN-RANDOMNESS';
const LOCAL_STORAGE_MAX_EPOCH = 'ZKLOGIN-MAX_EPOCH';
const LOCAL_STORAGE_ZK_ADDRESS = 'ZKLOGIN-ZK_ADDRESS';
// const LOCAL_STORAGE_ID_TOKEN = 'ZKLOGIN'-ID_TOKEN';
const LOCAL_STORAGE_ZKP = 'ZKLOGIN-ZKP';
const SUI_RPC_URL = import.meta.env.VITE_SUI_RPC_URL;
const PROVER_URL = import.meta.env.VITE_PROVER_URL;

const suiClient = new SuiClient({
	url: SUI_RPC_URL
});

type PartialZkLoginSignature = Omit<
	Parameters<typeof getZkLoginSignature>['0']['inputs'],
	'addressSeed'
>;

export async function prepare(): Promise<string> {
	console.log('Preparing for ZKLogin');
	const ephemeralKeyPair = new Ed25519Keypair();
	localStorage.setItem(LOCAL_STORAGE_SECRET_KEY, ephemeralKeyPair.getSecretKey());
	console.log('Ephemeral key pair acquired');
	const { epoch } = await suiClient.getLatestSuiSystemState();
	console.log('Sui epoch: ', epoch);
	const maxEpoch = Number(epoch) + 2;
	localStorage.setItem(LOCAL_STORAGE_MAX_EPOCH, maxEpoch.toString());
	const randomness = generateRandomness();
	localStorage.setItem(LOCAL_STORAGE_RANDOMNESS, randomness);
	console.log('Randomness generated');
	const nonce = generateNonce(ephemeralKeyPair.getPublicKey(), maxEpoch, randomness);
	console.log('Nonce generated');
	return nonce;
}

export async function receiveToken(idToken: string) {
	// const encodedJWT = urlParams.get('id_token');
	// const address = jwtToAddress(idToken);
	const maxEpoch = localStorage.getItem(LOCAL_STORAGE_MAX_EPOCH);
	const secret_key = localStorage.getItem(LOCAL_STORAGE_SECRET_KEY);
	// TODO: We should store the salt in the DB. Or use some salt server (sui provides this). If user lose the salt, they will need a new one which will result in a new address.
	let salt = localStorage.getItem(LOCAL_STORAGE_SALT);
	const randomness = localStorage.getItem(LOCAL_STORAGE_RANDOMNESS);
	let zkLoginUserAddress = localStorage.getItem(LOCAL_STORAGE_ZK_ADDRESS);

	if (!salt) {
		console.log('No salt found. Generating new one.');
		// Generate new salt if this is first time.
		const saltArray = crypto.getRandomValues(new Uint8Array(16));
		salt = BigInt(
			'0x' +
				Array.from(saltArray)
					.map((b) => b.toString(16).padStart(2, '0'))
					.join('')
		).toString();
		localStorage.setItem(LOCAL_STORAGE_SALT, salt);
	}
	zkLoginUserAddress = jwtToAddress(idToken, salt);
	console.log('ZKLogin user address: ', zkLoginUserAddress);
	localStorage.setItem(LOCAL_STORAGE_ZK_ADDRESS, zkLoginUserAddress);
	let ephemeralKeyPair;
	if (secret_key) {
		ephemeralKeyPair = Ed25519Keypair.fromSecretKey(secret_key);
	} else {
		ephemeralKeyPair = new Ed25519Keypair();
		localStorage.setItem(LOCAL_STORAGE_SECRET_KEY, ephemeralKeyPair.getSecretKey());
	}

	const extendedEphemeralPublicKey = getExtendedEphemeralPublicKey(ephemeralKeyPair.getPublicKey());
	const response = await fetch(PROVER_URL, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			jwt: idToken,
			extendedEphemeralPublicKey,
			maxEpoch: Number(maxEpoch),
			jwtRandomness: randomness,
			salt,
			keyClaimName: 'sub'
		})
	});
	const zkProofResult = await response.json();
	console.log('ZKProof result: ', zkProofResult);
	const partialLogin = zkProofResult as PartialZkLoginSignature;
	localStorage.setItem(LOCAL_STORAGE_ZKP, JSON.stringify(partialLogin));
}
