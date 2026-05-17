from open_webui.utils.totp import (
    generate_backup_codes,
    get_totp_step,
    hash_backup_code,
    hotp,
    normalize_backup_code,
    verify_backup_code,
    verify_totp,
)


RFC_SECRET = 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'


def test_hotp_matches_rfc_4226_vectors():
    expected = [
        '755224',
        '287082',
        '359152',
        '969429',
        '338314',
        '254676',
        '287922',
        '162583',
        '399871',
        '520489',
    ]

    for counter, code in enumerate(expected):
        assert hotp(RFC_SECRET, counter) == code


def test_verify_totp_matches_rfc_6238_sha1_vector():
    assert verify_totp(RFC_SECRET, '94287082', timestamp=59, digits=8, window=0) == get_totp_step(59)


def test_verify_totp_rejects_reused_time_step():
    step = get_totp_step(59)

    assert verify_totp(RFC_SECRET, '94287082', timestamp=59, digits=8, window=0, last_used_step=step) is None


def test_backup_code_hashing_normalizes_user_input():
    backup_code = generate_backup_codes(1)[0]
    hashed_code = hash_backup_code(backup_code)
    spaced_code = f' {backup_code.replace("-", " ")} '

    assert normalize_backup_code(spaced_code) == normalize_backup_code(backup_code)
    assert verify_backup_code(spaced_code, hashed_code)
    assert not verify_backup_code('wrong-code', hashed_code)
