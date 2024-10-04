import { useCurrentWallet, useSignAndExecuteTransaction } from '@mysten/dapp-kit';
import { bcs } from '@mysten/sui/bcs';
import { SuiClient, type SuiObjectData } from '@mysten/sui/client';
import { Transaction } from '@mysten/sui/transactions';

const SUI_RANDOMNESS_STATE_OBJECT_ID =
	'0x0000000000000000000000000000000000000000000000000000000000000008';
// const SUI_REQUEST_AMOUNT = 250_000_000;

export function floatToUint32(value: number): number {
	// Create a buffer of 4 bytes (32 bits)
	const buffer = new ArrayBuffer(4);

	// Create a DataView view on the buffer
	const dataView = new DataView(buffer);

	// Create a Uint32Array view on the buffer
	const intView = new Uint32Array(buffer);

	// Set the float value as little endian
	dataView.setFloat32(0, value, true);

	// Return the bitwise representation as an unsigned 32-bit integer
	return intView[0];
}

export class Sui {
	public client: SuiClient;
	private packageId: string = import.meta.env.VITE_SUI_ATOMA_PACKAGE;
	private atomaDb: string = import.meta.env.VITE_SUI_ATOMA_DB_PACKAGE;
	private toma: string = import.meta.env.VITE_SUI_TOMA_PACKAGE;
	private signAndExecuteTransaction: any;
	private currentWallet: any;

	constructor(currentWallet: any, signAndExecuteTransaction: any) {
		this.client = new SuiClient({
			url: import.meta.env.VITE_SUI_RPC_URL
		});
		this.signAndExecuteTransaction = signAndExecuteTransaction;
		this.currentWallet = currentWallet;
	}

	async getTomaWallet(): Promise<SuiObjectData> {
		const accountAddress = this.currentWallet.accounts[0].address;
		const tomaObject = await this.client.getOwnedObjects({
			owner: accountAddress,
			filter: {
				StructType: `0x2::coin::Coin<${this.toma}::toma::TOMA>`
			},
			limit: 50
		});
		for (const object of tomaObject.data) {
			if (object.data?.objectId) {
				try {
					let result = await this.client.getObject({
						id: object.data?.objectId,
						options: {
							showContent: true
						}
					});
					// TODO: what's the minimum balance?
					if (result.data.content?.['fields']?.['balance'] > 1000000) {
						// We found the wallet
						return object.data;
					}
				} catch (err) {
					console.error(err);
				}
			}
		}
		throw new Error('Toma wallet not found');
	}

	public async send_image_prompt(
		model: string,
		output_destination: Uint8Array,
		max_fee_per_token: number,
		input_source: Uint8Array,
		width: number,
		height: number,
		onSuccess: Function,
		onError: Function,
		onSettled: Function
	) {
		const tx = new Transaction();
		tx.setGasBudget(15000000);
		// const gasCoin = tx.splitCoins(tx.gas, [SUI_REQUEST_AMOUNT]);
		// Text-to-image
		let tomaWallet = await this.getTomaWallet();
		tx.moveCall({
			target: `${this.packageId}::prompts::send_image_prompt`,
			arguments: [
				tx.object(this.atomaDb), // atoma
				tx.objectRef(tomaWallet), // wallet
				tx.pure.string(model), // model
				tx.pure(bcs.vector(bcs.U8).serialize(input_source)), // prompt
				tx.pure(bcs.vector(bcs.U8).serialize(new Uint8Array())), // uncond_prompt
				tx.pure.u64(height), // height
				tx.pure.u64(width), // width
				tx.pure.u32(floatToUint32(1)), // guidance_scale
				tx.pure(bcs.option(bcs.vector(bcs.U8)).serialize(null)), // img2img
				tx.pure.u32(floatToUint32(1)), // img2img_strength
				tx.pure.u64(1), // num_samples
				tx.pure.u64(40), // n_steps
				tx.pure(bcs.vector(bcs.U8).serialize(output_destination)), // output_destination
				tx.pure.u64(max_fee_per_token), // max_fee_per_input_token
				tx.pure.u64(max_fee_per_token), // max_fee_per_output_pixel
				tx.pure(bcs.option(bcs.U64).serialize(null)), // nodes_to_sample
				tx.object(SUI_RANDOMNESS_STATE_OBJECT_ID) // random
			]
		});
		this.send(tx, onSuccess, onError, onSettled);
	}

	public async send_text_prompt(
		model: string,
		output_destination: Uint8Array,
		max_fee_per_token: number,
		input_source: Uint8Array,
		streamingEnabled: boolean,
		max_tokens: number,
		onSuccess: Function,
		onError: Function
	) {
		const tx = new Transaction();
		tx.setGasBudget(15000000);
		// Text-to-text
		console.log('currentWallet', this.currentWallet);
		let tomaWallet = await this.getTomaWallet();
		console.log('tomaWallet', tomaWallet);
		tx.moveCall({
			target: `${this.packageId}::prompts::send_prompt`,
			arguments: [
				tx.object(this.atomaDb), // atoma
				tx.objectRef(tomaWallet), // wallet
				tx.pure.string(model), // model
				tx.pure(bcs.vector(bcs.U8).serialize(output_destination)), // output_destination
				tx.pure(bcs.vector(bcs.U32).serialize(new Uint32Array())), // pre_prompt_tokens
				tx.pure.bool(true), // prepend_output_with_input
				tx.pure.u64(max_fee_per_token), // max_fee_per_token
				tx.pure(bcs.vector(bcs.U8).serialize(input_source)), // prompt
				tx.pure.bool(streamingEnabled), // should_stream_output
				tx.pure.u64(max_tokens), // max_tokens
				tx.pure.u64(100), // repeat_last_n
				tx.pure.u32(floatToUint32(1.1)), // repeat_penalty
				tx.pure.u32(floatToUint32(0.75)), // temperature
				tx.pure.u64(1), // top_k
				tx.pure.u32(floatToUint32(1)), // top_p
				tx.pure(bcs.option(bcs.U64).serialize(null)), // nodes_to_sample
				tx.object(SUI_RANDOMNESS_STATE_OBJECT_ID) // random
			]
		});
		return await this.send(tx, onSuccess, onError);
	}

	async send(tx: Transaction, onSuccess: Function, onError: Function) {
		return await this.signAndExecuteTransaction(
			{ transaction: tx },
			{
				onSuccess,
				onError
			}
		);
	}
}
