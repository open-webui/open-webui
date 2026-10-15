//! The browser worker is the only owner. No persistence, export, or logging API.
use base64::{engine::general_purpose::STANDARD as B64, Engine};
use openmls::prelude::*;
use openmls_basic_credential::SignatureKeyPair;
use openmls_rust_crypto::OpenMlsRustCrypto;
use openmls_traits::OpenMlsProvider;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use tls_codec::{Deserialize as TlsDeserialize, Serialize as TlsSerialize};
use wasm_bindgen::prelude::*;

const SUITE: Ciphersuite = Ciphersuite::MLS_128_DHKEMX25519_AES128GCM_SHA256_Ed25519;
const MAX_PACKET: usize = 1024 * 1024;
fn err<T>(_: T) -> String { "Invalid session operation".into() }
fn require(ok: bool) -> Result<(), String> { if ok { Ok(()) } else { Err(err(())) } }
fn encode<T: TlsSerialize>(v: &T) -> Result<String, String> { Ok(B64.encode(v.tls_serialize_detached().map_err(err)?)) }
fn decode(v: &str) -> Result<Vec<u8>, String> {
    require(v.len() <= MAX_PACKET * 4 / 3 + 4)?;
    let bytes = B64.decode(v).map_err(err)?;
    require(bytes.len() <= MAX_PACKET)?;
    Ok(bytes)
}
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct Identity { channel: String, session: String, user: String, participation: String }
#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Binding { identity: Identity, key: String }
fn identity(cred: &Credential) -> Result<Identity, String> {
    let basic = BasicCredential::try_from(cred.clone()).map_err(err)?;
    serde_json::from_slice(basic.identity()).map_err(err)
}
fn check(cred: &Credential, key: &[u8], context: &Identity, roster: &[Binding]) -> Result<Identity, String> {
    let id = identity(cred)?;
    require(id.channel == context.channel && id.session == context.session)?;
    require(roster.iter().any(|b| b.identity == id && b.key == B64.encode(key)))?;
    Ok(id)
}
fn roster(value: &str, context: &Identity) -> Result<Vec<Binding>, String> {
    let roster: Vec<Binding> = serde_json::from_str(value).map_err(err)?;
    require(!roster.is_empty() && roster.len() <= 128)?;
    let mut users = std::collections::HashSet::new();
    let mut participations = std::collections::HashSet::new();
    for b in &roster {
        require(b.identity.channel == context.channel && b.identity.session == context.session
            && users.insert(&b.identity.user) && participations.insert(&b.identity.participation)
            && decode(&b.key)?.len() == 32)?;
    }
    Ok(roster)
}

#[wasm_bindgen]
pub struct Session {
    provider: OpenMlsRustCrypto,
    signer: SignatureKeyPair,
    credential: CredentialWithKey,
    id: Identity,
    host: String,
    group: Option<MlsGroup>,
}
#[wasm_bindgen]
impl Session {
    #[wasm_bindgen(constructor)]
    pub fn new(identity_json: &str, host: &str) -> Result<Session, String> {
        let id: Identity = serde_json::from_str(identity_json).map_err(err)?;
        require([&id.channel, &id.session, &id.user, &id.participation].iter()
            .all(|s| !s.is_empty() && s.len() <= 128) && !host.is_empty())?;
        let provider = OpenMlsRustCrypto::default();
        let signer = SignatureKeyPair::new(SignatureScheme::ED25519).map_err(err)?;
        signer.store(provider.storage()).map_err(err)?;
        let credential = CredentialWithKey {
            credential: BasicCredential::new(serde_json::to_vec(&id).map_err(err)?).into(),
            signature_key: signer.public().into(),
        };
        Ok(Self { provider, signer, credential, id, host: host.into(), group: None })
    }
    pub fn public_key(&self) -> String { B64.encode(self.signer.public()) }
    pub fn key_package(&self) -> Result<String, String> {
        require(self.group.is_none())?;
        let kp = KeyPackage::builder().build(SUITE, &self.provider, &self.signer, self.credential.clone()).map_err(err)?;
        encode(kp.key_package())
    }
    pub fn create(&mut self) -> Result<(), String> {
        require(self.group.is_none() && self.id.participation == self.host)?;
        self.group = Some(MlsGroup::builder().ciphersuite(SUITE)
            .use_ratchet_tree_extension(true)
            .set_past_epoch_deletion_policy(PastEpochDeletionPolicy::MaxEpochs(0))
            .with_group_id(GroupId::from_slice(self.id.session.as_bytes()))
            .build(&self.provider, &self.signer, self.credential.clone()).map_err(err)?);
        Ok(())
    }
    pub fn join(&mut self, welcome: &str, bindings: &str) -> Result<(), String> {
        require(self.group.is_none() && self.id.participation != self.host)?;
        let roster = roster(bindings, &self.id)?;
        let msg = MlsMessageIn::tls_deserialize_exact(decode(welcome)?).map_err(err)?;
        let welcome = match msg.extract() { MlsMessageBodyIn::Welcome(w) => w, _ => return Err(err(())) };
        let config = MlsGroupJoinConfig::builder().use_ratchet_tree_extension(true)
            .set_past_epoch_deletion_policy(PastEpochDeletionPolicy::MaxEpochs(0)).build();
        let group = StagedWelcome::new_from_welcome(&self.provider, &config, welcome, None).map_err(err)?
            .into_group(&self.provider).map_err(err)?;
        require(group.group_id().as_slice() == self.id.session.as_bytes() && group.ciphersuite() == SUITE)?;
        let mut users = std::collections::HashSet::new();
        let mut found_host = false;
        for m in group.members() {
            let id = check(&m.credential, &m.signature_key, &self.id, &roster)?;
            require(users.insert(id.user))?;
            found_host |= id.participation == self.host;
        }
        require(found_host)?;
        self.group = Some(group);
        Ok(())
    }
    pub fn add(&mut self, key_package: &str, expected: &str, bindings: &str) -> Result<String, String> {
        require(self.id.participation == self.host)?;
        let roster = roster(bindings, &self.id)?;
        let kp = KeyPackageIn::tls_deserialize_exact(decode(key_package)?).map_err(err)?
            .validate(self.provider.crypto(), ProtocolVersion::Mls10).map_err(err)?;
        let id = check(kp.leaf_node().credential(), kp.leaf_node().signature_key().as_slice(), &self.id, &roster)?;
        require(id.participation == expected)?;
        let group = self.group.as_mut().ok_or_else(|| err(()))?;
        require(group.members().count() < 128 && !group.members().any(|m| identity(&m.credential).is_ok_and(|i| i.user == id.user)))?;
        let (commit, welcome, _) = group.add_members(&self.provider, &self.signer, &[kp]).map_err(err)?;
        let result = json!({"commit": encode(&commit)?, "welcome": encode(&welcome)?});
        group.merge_pending_commit(&self.provider).map_err(err)?;
        Ok(result.to_string())
    }
    pub fn remove(&mut self, participation: &str, bindings: &str) -> Result<String, String> {
        require(self.id.participation == self.host && participation != self.host)?;
        let roster = roster(bindings, &self.id)?;
        require(!roster.iter().any(|b| b.identity.participation == participation))?;
        let group = self.group.as_mut().ok_or_else(|| err(()))?;
        let index = group.members().find(|m| identity(&m.credential).is_ok_and(|i| i.participation == participation))
            .ok_or_else(|| err(()))?.index;
        let (commit, _, _) = group.remove_members(&self.provider, &self.signer, &[index]).map_err(err)?;
        let out = encode(&commit)?;
        group.merge_pending_commit(&self.provider).map_err(err)?;
        Ok(out)
    }
    pub fn update(&mut self) -> Result<String, String> {
        let group = self.group.as_mut().ok_or_else(|| err(()))?;
        if self.id.participation == self.host {
            let bundle = group.self_update(&self.provider, &self.signer, LeafNodeParameters::default()).map_err(err)?;
            let out = encode(bundle.commit())?;
            group.merge_pending_commit(&self.provider).map_err(err)?;
            Ok(out)
        } else {
            let (proposal, _) = group.propose_self_update(&self.provider, &self.signer, LeafNodeParameters::default()).map_err(err)?;
            encode(&proposal)
        }
    }
    pub fn commit_updates(&mut self) -> Result<String, String> {
        require(self.id.participation == self.host)?;
        let group = self.group.as_mut().ok_or_else(|| err(()))?;
        let (commit, _, _) = group.commit_to_pending_proposals(&self.provider, &self.signer).map_err(err)?;
        let out = encode(&commit)?;
        group.merge_pending_commit(&self.provider).map_err(err)?;
        Ok(out)
    }
    pub fn encrypt(&mut self, text: &str) -> Result<String, String> {
        require(text.len() <= 100 * 1024)?; // Includes the authenticated receipt/message envelope.
        let group = self.group.as_mut().ok_or_else(|| err(()))?;
        encode(&group.create_message(&self.provider, &self.signer, text.as_bytes()).map_err(err)?)
    }
    pub fn process(&mut self, packet: &str, expected: &str, bindings: &str) -> Result<String, String> {
        let roster = roster(bindings, &self.id)?;
        let group = self.group.as_mut().ok_or_else(|| err(()))?;
        let msg = MlsMessageIn::tls_deserialize_exact(decode(packet)?).map_err(err)?;
        let processed = group.process_message(&self.provider, msg.try_into_protocol_message().map_err(err)?).map_err(err)?;
        let index = match processed.sender() { Sender::Member(i) => *i, _ => return Err(err(())) };
        let member = group.member_at(index).ok_or_else(|| err(()))?;
        let sender = check(processed.credential(), &member.signature_key, &self.id, &roster)?;
        require(sender.participation == expected)?;
        let result = match processed.into_content() {
            ProcessedMessageContent::ApplicationMessage(m) => {
                let bytes = m.into_bytes();
                require(bytes.len() <= 100 * 1024)?;
                json!({"kind":"application", "sender":sender, "text":String::from_utf8(bytes).map_err(err)?})
            },
            ProcessedMessageContent::ProposalMessage(p) => {
                match p.proposal() {
                    Proposal::Update(u) => {
                        let id = check(u.leaf_node().credential(), u.leaf_node().signature_key().as_slice(), &self.id, &roster)?;
                        require(id == sender)?;
                    },
                    _ => return Err(err(())),
                }
                group.store_pending_proposal(self.provider.storage(), *p).map_err(err)?;
                json!({"kind":"proposal"})
            },
            ProcessedMessageContent::StagedCommitMessage(c) => {
                require(sender.participation == self.host)?;
                if let Some(leaf) = c.update_path_leaf_node() {
                    require(check(leaf.credential(), leaf.signature_key().as_slice(), &self.id, &roster)? == sender)?;
                }
                let mut added_users = std::collections::HashSet::new();
                for p in c.queued_proposals() {
                    match p.proposal() {
                        Proposal::Add(a) => {
                            let leaf = a.key_package().leaf_node();
                            let id = check(leaf.credential(), leaf.signature_key().as_slice(), &self.id, &roster)?;
                            require(added_users.insert(id.user.clone()) && !group.members().any(|m| identity(&m.credential).is_ok_and(|i| i.user == id.user)))?;
                        },
                        Proposal::Remove(r) => {
                            let m = group.member_at(r.removed()).ok_or_else(|| err(()))?;
                            let id = identity(&m.credential)?;
                            require(id.participation != self.host && !roster.iter().any(|b| b.identity == id))?;
                        },
                        Proposal::Update(u) => {
                            let idx = match p.sender() { Sender::Member(i) => *i, _ => return Err(err(())) };
                            let old = group.member_at(idx).ok_or_else(|| err(()))?;
                            require(check(u.leaf_node().credential(), u.leaf_node().signature_key().as_slice(), &self.id, &roster)? == identity(&old.credential)?)?;
                        },
                        _ => return Err(err(())),
                    }
                }
                require(group.members().count() + c.add_proposals().count() - c.remove_proposals().count() <= 128)?;
                group.merge_staged_commit(&self.provider, *c).map_err(err)?;
                json!({"kind":"commit"})
            },
            _ => return Err(err(())),
        };
        Ok(result.to_string())
    }
    pub fn members(&self) -> Result<String, String> {
        let group = self.group.as_ref().ok_or_else(|| err(()))?;
        let mut members = Vec::<Value>::new();
        for m in group.members() {
            let id = identity(&m.credential)?;
            let mut hash = Sha256::new();
            hash.update(b"Open WebUI temporary chat identity v1\0");
            hash.update(serde_json::to_vec(&id).map_err(err)?);
            hash.update(&m.signature_key);
            members.push(json!({"identity":id,"fingerprint":format!("{:x}",hash.finalize())}));
        }
        Ok(json!(members).to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn client(n: usize, session: &str) -> Session {
        Session::new(&json!({"channel":"c","session":session,"user":format!("u{n}"),"participation":format!("p{n}")}).to_string(), "p0").unwrap()
    }
    fn bindings(clients: &[&Session]) -> String {
        json!(clients.iter().map(|c| json!({"identity":c.id,"key":c.public_key()})).collect::<Vec<_>>()).to_string()
    }
    #[test]
    fn bindings_membership_and_epochs() {
        let mut a = client(0,"s"); let mut b = client(1,"s"); let c = client(2,"other-session");
        a.create().unwrap();
        let roster = bindings(&[&a,&b]);
        assert!(a.add(&c.key_package().unwrap(), "p2", &roster).is_err());
        let old = a.encrypt("past epoch").unwrap();
        let added: Value = serde_json::from_str(&a.add(&b.key_package().unwrap(), "p1", &roster).unwrap()).unwrap();
        b.join(added["welcome"].as_str().unwrap(), &roster).unwrap();
        assert!(b.process(&old,"p0",&roster).is_err());
        let msg = a.encrypt("hello").unwrap();
        assert!(b.process(&msg,"p0",&roster).unwrap().contains("hello"));
        assert!(b.process(&msg,"p0",&roster).is_err());
        // A valid MLS commit from an ordinary member must still be rejected.
        let bundle = b.group.as_mut().unwrap().self_update(&b.provider,&b.signer,LeafNodeParameters::default()).unwrap();
        assert!(a.process(&encode(bundle.commit()).unwrap(),"p1",&roster).is_err());
        assert!(b.remove("p0", &roster).is_err());
    }
}
