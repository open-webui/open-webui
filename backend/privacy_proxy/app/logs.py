SEP = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"


def log_sep(): print(SEP)

def log_garnet(session_id, provider, privacy, model, path):
    print(f"[GARNET] session={session_id[:8]} provider={provider} privacy={'ON' if privacy else 'OFF'} model={model} path={path}")

def log_entity_filter(enabled_types):
    print(f"[ENTITY FILTER] active → only: {enabled_types}")

def log_in_user(text):
    print(f"[IN  USER] {text[:200]}")

def log_out_user(text):
    print(f"[OUT USER] {text[:200]}")

def log_no_pii():
    print(f"[NO PII] message unchanged — no entities detected")

def log_in_file(role, length, text):
    print(f"[IN  FILE] role={role} len={length} | {text[:200]}")

def log_out_file(text):
    print(f"[OUT FILE] {text[:200]}")

def log_large_file(length, n_chunks):
    print(f"[LARGE FILE] {length} chars → chunked pseudo ({n_chunks} chunks)")

def log_out_file_chunked(n_chunks, total_chars):
    print(f"[OUT FILE] chunked {n_chunks} parts → {total_chars} chars")

def log_file_scan(count):
    print(f"[FILE SCAN] {count} RAG chunk(s) processed")

def log_file_pii(count, breakdown):
    print(f"[FILE PII] {count} new entities detected | breakdown={breakdown or 'in-memory-only'}")

def log_file_pii_duplicate():
    print(f"[FILE PII] 0 new entities — already in mapping (duplicate upload)")

def log_internal(internal_type):
    print(f"[INTERNAL] type={internal_type} → skipped pseudonymization")

def log_privacy_off():
    print(f"[PRIVACY OFF] forwarding raw → no pseudonymization")

def log_history_depseudo(count):
    print(f"[HISTORY DEPSEUDO] restored tokens in {count} assistant message(s)")

def log_to_llm(url, model):
    print(f"[→ LLM   ] {url} | model={model}")

def log_from_llm(chunk_text):
    print(f"[← LLM   ] {repr(chunk_text[:200])}")

def log_to_user(token_count):
    print(f"[→ USER  ] depseudo complete, {token_count} tokens in mapping")

def log_mapping(session_id, total_tokens):
    print(f"[MAPPING] session={session_id[:8]} total_tokens={total_tokens}")

def log_self_loop(resolved_url):
    print(f"[SELF-LOOP] detected → resolved to {resolved_url}")

def log_responses_api(model):
    print(f"[RESPONSES API] model={model} → using /responses endpoint")

def log_image(model, prompt, url):
    print(f"[IMAGE] model={model} prompt={prompt[:80]} → {url}")

def log_health():
    print(f"[HEALTH] ping received → ok")

def log_vault_start(file_id, session_id, enabled_types):
    print(f"[VAULT START] file_id={file_id} session={session_id} entity_filter={enabled_types or 'ALL'}")

def log_vault_done(file_id, count, report):
    print(f"[VAULT DONE] file_id={file_id} → {count} new entities | breakdown={report}")

def log_vault_skip(file_id):
    print(f"[VAULT SKIP] privacy=OFF file_id={file_id}")

def log_vault_error(field):
    print(f"[VAULT ERROR] missing {field} field")

def log_analyze(language, enabled_types, text):
    print(f"[ANALYZE] lang={language or 'auto'} filter={enabled_types or 'ALL'} text={text[:100]}")

def log_analyze_result(count, types):
    print(f"[ANALYZE RESULT] {count} entities found → {types}")

def log_error(msg):
    print(f"[ERROR] {msg}")

def log_error_passthrough(status, url, body):
    print(f"[ERROR] passthrough status={status} url={url} body={body[:200]}")# test
# test
# test
# retest
