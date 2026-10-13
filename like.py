import json
import os
import requests
import urllib3
import time
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

import like_pb2, like_count_pb2, uid_generator_pb2
from google.protobuf.json_format import MessageToJson

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ACCS_FILE = 'accs.txt'
xK, xV = b'Yg&tc%DEuh6%Zc^8', b'6oyZDr22E3ychjM%'
REGION = "ME"
LOGIN_HOST = "https://loginbp.ppmainecoonghj.com"
CLIENT_URL_FALLBACK = "https://clientbp.ppmainecoonghj.com"
MAX_WORKERS = 60
LOGIN_WORKERS = 30
TIMEOUT = 8


def EnC_Vr(n):
    out = []
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            b |= 0x80
        out.append(b)
        if not n:
            break
    return bytes(out)


def CrEaTe_VarianT(fn, v):
    return EnC_Vr((fn << 3) | 0) + EnC_Vr(v)


def CrEaTe_LenGTh(fn, v):
    if isinstance(v, str):
        enc = v.encode('latin-1', errors='ignore')
    elif isinstance(v, (bytes, bytearray)):
        enc = bytes(v)
    else:
        enc = str(v).encode()
    return EnC_Vr((fn << 3) | 2) + EnC_Vr(len(enc)) + enc


def CrEaTe_ProTo(fields):
    p = bytearray()
    for f, v in fields.items():
        if isinstance(v, dict):
            p.extend(CrEaTe_LenGTh(f, bytes(CrEaTe_ProTo(v))))
        elif isinstance(v, int):
            p.extend(CrEaTe_VarianT(f, v))
        elif isinstance(v, (str, bytes)):
            p.extend(CrEaTe_LenGTh(f, v))
    return bytes(p)


def _read_varint(data, pos):
    r = 0
    s = 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        r |= (b & 0x7F) << s
        if not (b & 0x80):
            break
        s += 7
    return r, pos


def _parse_pb(data):
    fields = {}
    pos = 0
    n = len(data)
    while pos < n:
        try:
            key, pos = _read_varint(data, pos)
        except:
            break
        fn = key >> 3
        wt = key & 7
        try:
            if wt == 0:
                val, pos = _read_varint(data, pos)
            elif wt == 2:
                ln, pos = _read_varint(data, pos)
                val = data[pos:pos + ln]
                pos += ln
            elif wt == 5:
                val = data[pos:pos + 4]
                pos += 4
            elif wt == 1:
                val = data[pos:pos + 8]
                pos += 8
            else:
                break
        except:
            break
        fields.setdefault(fn, []).append(val)
    return fields


def _gv(f, n):
    v = f.get(n)
    if v is None:
        return None
    if isinstance(v, list):
        v = v[0]
    return v


def _safe_decode(v):
    if v is None:
        return None
    if isinstance(v, str):
        return v
    if isinstance(v, bytes):
        for enc in ('utf-8', 'utf-8-sig', 'latin-1'):
            try:
                return v.decode(enc)
            except:
                continue
        return v.decode('latin-1', errors='ignore')
    return str(v)


def StripPrefix(body):
    if len(body) <= 64:
        return body
    try:
        if 8 in _parse_pb(body):
            return body
    except:
        pass
    try:
        if 8 in _parse_pb(body[64:]):
            return body[64:]
    except:
        pass
    return body[64:]


def Ua():
    return '5.3.0B1'


def PyL(access_token, open_id, region=REGION):
    P = {}
    P[3] = "2026-10-01 01:44:06"
    P[4] = "free fire"
    P[5] = 1
    P[7] = "1.132.9"
    P[8] = "Android OS 14 / API-34 (UP1A.231005.007/V816.0.15.0.UNQMIXM)"
    P[9] = "Handheld"
    P[10] = "Grameenphone"
    P[11] = "CarrierDataNetwork"
    P[12] = 1666
    P[13] = 750
    P[14] = "352"
    P[15] = "ARM64 FP ASIMD AES | 2400 | 8"
    P[16] = 5563
    P[17] = "Mali-G57 MC2"
    P[18] = "OpenGL ES 3.2 v1.r32p1-01eac0.0a0b917d9265b4c01be9925306306139"
    P[19] = "Google|9cc73f7a-91f6-40f6-87ec-5b67e597eb8c"
    P[20] = "59.152.5.188"
    P[21] = "en"
    P[22] = open_id
    P[23] = "8"
    P[24] = "Handheld"
    P[25] = "Xiaomi 2312DRAABI"
    P[26] = region
    P[29] = access_token
    P[30] = 1
    P[41] = "Grameenphone"
    P[42] = "Cellular"
    P[57] = "7428b253defc164018c604a1ebbfebdf"
    P[60] = 109685
    P[61] = 58294
    P[62] = 797
    P[63] = 18000
    P[64] = 58818
    P[65] = 109685
    P[66] = 58818
    P[67] = 109685
    P[73] = 2
    P[74] = "/data/app/~~cqQgpdMykLQEM3odipXatw==/com.dts.freefireth-G6e5yOt1dtuXG5Ambhj18g==/lib/arm64"
    P[76] = 1
    P[77] = "b8e0cd5e295eee42f5860d3c86e483dd|/data/app/~~cqQgpdMykLQEM3odipXatw==/com.dts.freefireth-G6e5yOt1dtuXG5Ambhj18g==/base.apk"
    P[78] = 3
    P[79] = 2
    P[81] = "64"
    P[83] = "2019121229"
    P[85] = 3
    P[86] = "OpenGLES2"
    P[87] = 4095
    P[88] = 8
    P[89] = b"FwQVTgUPX1UaUllDDwcWCRBpWAUOUgsvA1snWlBaO1kFYg=="
    P[90] = "Dhaka"
    P[91] = "C"
    P[92] = 8043
    P[93] = "android"
    P[94] = "KqsHT4XbSZhqerDNUhjbS3DxG/4+I62zQU2tZFJN91kBUICAlZ5yujshLKvjlk/KiShfKfis8EeB1PMhFHIodWPncZC4fCHYF3TcTwNj95aWY/S3"
    P[95] = 111207
    P[96] = '{"cur_rate":[60,90,120],"support_etc2":false}'
    P[97] = 1
    P[98] = 1
    P[99] = "4"
    P[100] = "4"
    P[102] = "GQ]        e"
    P[103] = 1
    P[104] = 45174
    P[105] = 1
    P[106] = "https://dl-bs.ggpolarbear.com/live/ABHotUpdates/|https://core-bs.ggpolarbear.com/live/ABHotUpdates/|a4332cb1c1a84e51dd77441e4856ed5a"
    P[107] = "1.9393e7b8e53e8aeb"
    return AES.new(xK, AES.MODE_CBC, xV).encrypt(pad(CrEaTe_ProTo(P), 16))


_session = requests.Session()
_session.verify = False


def GeT_AccEss(uid, password):
    url = "https://100067.connect.garena.com/api/v2/oauth/guest/token:grant"
    headers = {"User-Agent": Ua(), "Content-Type": "application/json; charset=utf-8"}
    try:
        R = _session.post(url, headers=headers, json={
            "client_id": 100067,
            "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
            "client_type": 2,
            "device_id": "",
            "password": password,
            "response_type": "token",
            "uid": int(uid)
        }, timeout=TIMEOUT)
    except:
        return None
    if R.status_code not in (200, 201):
        return None
    try:
        J = R.json()
    except:
        return None
    if J.get("code") != 0:
        return None
    d = J.get("data", {})
    return {"access_token": d.get("access_token"), "open_id": d.get("open_id")}


def MajorLogin(payload):
    url = f"{LOGIN_HOST}/MajorLogin"
    headers = {
        "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "Accept": "*/*",
        "Accept-Encoding": "deflate, gzip",
        "X-GA-SV": str(int(time.time())),
        "Authorization": "Bearer ",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB55",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1"
    }
    try:
        R = _session.post(url, headers=headers, data=payload, timeout=TIMEOUT)
    except:
        return None
    return R.content if R.status_code in (200, 201) and R.content else None


def GeTLoginDaTa(client_url, payload, jwt):
    url = f"{client_url}/GetLoginData"
    headers = {
        "User-Agent": "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        "Accept": "*/*",
        "Accept-Encoding": "deflate, gzip",
        "X-GA-SV": str(int(time.time())),
        "Authorization": f"Bearer {jwt}",
        "X-GA": "v1 1",
        "ReleaseVersion": "OB55",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Unity-Version": "2018.4.12f1"
    }
    try:
        R = _session.post(url, headers=headers, data=payload, timeout=TIMEOUT)
    except:
        return None
    return R.content if R.status_code == 200 and R.content else None


def ExtractMajorLogin(ml):
    body = StripPrefix(ml)
    f = _parse_pb(body)
    return {
        "jwt": _safe_decode(_gv(f, 8)),
        "url": _safe_decode(_gv(f, 10)) or CLIENT_URL_FALLBACK,
        "ts": _gv(f, 21) if isinstance(_gv(f, 21), int) else None,
        "key": _gv(f, 22) if isinstance(_gv(f, 22), bytes) else None,
        "iv": _gv(f, 23) if isinstance(_gv(f, 23), bytes) else None,
        "account_id": _gv(f, 1) if isinstance(_gv(f, 1), int) else None
    }


def login(uid, password):
    td = GeT_AccEss(uid, password)
    if not td:
        return None
    at, oid = td["access_token"], td["open_id"]
    pl = PyL(at, oid, REGION)
    ml = MajorLogin(pl)
    if not ml:
        return None
    ad = ExtractMajorLogin(ml)
    if not ad.get("jwt") or not ad.get("key") or not ad.get("iv"):
        return None
    ld = GeTLoginDaTa(ad["url"], pl, ad["jwt"])
    if not ld:
        return None
    gl = _parse_pb(ld)
    chat = _safe_decode(_gv(gl, 14))
    if not chat:
        return None
    host, port = chat.split(":")
    return {
        "jwt": ad["jwt"],
        "ts": ad["ts"],
        "key": ad["key"],
        "iv": ad["iv"],
        "account_id": ad["account_id"] or uid,
        "chat_host": host,
        "chat_port": port,
        "uid": uid,
        "password": password
    }


KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
UNITY_VERSION = "2018.4.12f1"
RELEASE_VER = "OB55"


def encrypt_data(plain_text):
    if isinstance(plain_text, str):
        plain_text = bytes.fromhex(plain_text)
    cipher = AES.new(KEY, AES.MODE_CBC, IV)
    return cipher.encrypt(pad(plain_text, AES.block_size)).hex()


def create_uid_proto(uid):
    pb = uid_generator_pb2.uid_generator()
    pb.saturn_ = int(uid)
    pb.garena = 1
    return pb.SerializeToString()


def create_like_proto(uid):
    pb = like_pb2.like()
    pb.uid = int(uid)
    return pb.SerializeToString()


def get_player_info(uid, jwt):
    enc_uid = encrypt_data(create_uid_proto(uid))
    headers = {
        'User-Agent': "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Authorization': f"Bearer {jwt}",
        'Content-Type': "application/x-www-form-urlencoded",
        'X-Unity-Version': UNITY_VERSION,
        'X-GA': "v1 1",
        'ReleaseVersion': RELEASE_VER,
    }
    try:
        res = _session.post(
            f"{CLIENT_URL_FALLBACK}/GetPlayerPersonalShow",
            data=bytes.fromhex(enc_uid),
            headers=headers,
            timeout=TIMEOUT
        )
        if res.status_code == 200:
            pb = like_count_pb2.Info()
            pb.ParseFromString(res.content)
            data = json.loads(MessageToJson(pb))
            acc = data.get("AccountInfo", {})
            likes = int(acc.get("Likes", 0))
            nick = acc.get("PlayerNickname", "Unknown")
            level = int(acc.get("Level", 0))
            return nick, likes, level
    except Exception:
        pass
    return None, 0, 0


def _send_one_like(jwt, enc_like, headers):
    try:
        r = _session.post(
            f"{CLIENT_URL_FALLBACK}/LikeProfile",
            headers={**headers, "Authorization": f"Bearer {jwt}"},
            data=bytes.fromhex(enc_like),
            timeout=TIMEOUT
        )
        return r.status_code == 200
    except Exception:
        return False


def send_likes_once(uid, jwts):
    if not jwts:
        return None, 0, 0, 0
    nick, before, _ = get_player_info(uid, jwts[0])
    enc_like = encrypt_data(create_like_proto(uid))
    headers = {
        'User-Agent': "UnityPlayer/2018.4.12f1 (UnityWebRequest/1.0, libcurl/8.5.0-DEV)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/x-www-form-urlencoded",
        'X-Unity-Version': UNITY_VERSION,
        'X-GA': "v1 1",
        'ReleaseVersion': RELEASE_VER,
    }
    sent = 0
    workers = min(len(jwts), MAX_WORKERS)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_send_one_like, jwt, enc_like, headers) for jwt in jwts]
        for f in as_completed(futures):
            try:
                if f.result():
                    sent += 1
            except Exception:
                pass
    failed = len(jwts) - sent
    print(f"{uid}: ok {sent}/{len(jwts)} fail {failed}")
    time.sleep(2)
    _, after, _ = get_player_info(uid, jwts[0])
    return nick, before, after, sent


def load_accounts():
    accounts = []
    if not os.path.exists(ACCS_FILE):
        print(f"[!] {ACCS_FILE} not found")
        return accounts
    with open(ACCS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) >= 2:
                uid = parts[0].strip()
                pw = parts[1].strip()
                if uid and pw:
                    accounts.append((uid, pw))
    return accounts


def _try_login_one(args):
    i, total, uid, pwd = args
    try:
        bot = login(uid, pwd)
        if bot and bot.get("jwt"):
            return (i, total, uid, pwd, bot, None)
        return (i, total, uid, pwd, None, "fail")
    except Exception as e:
        return (i, total, uid, pwd, None, str(e)[:60])


def check_all_accounts():
    accounts = load_accounts()
    if not accounts:
        return []
    print(f"[*] Total accounts: {len(accounts)}")
    print(f"[*] Logging in with {LOGIN_WORKERS} threads...\n")
    working = []
    failed = []
    total = len(accounts)
    tasks = [(i, total, uid, pwd) for i, (uid, pwd) in enumerate(accounts, 1)]
    with ThreadPoolExecutor(max_workers=LOGIN_WORKERS) as ex:
        futures = [ex.submit(_try_login_one, t) for t in tasks]
        for f in as_completed(futures):
            i, total, uid, pwd, bot, err = f.result()
            if bot:
                working.append({
                    "uid": uid,
                    "pw": pwd,
                    "jwt": bot["jwt"],
                    "account_id": bot["account_id"],
                    "chat_host": bot["chat_host"],
                    "chat_port": bot["chat_port"],
                })
                print(f"[{i}/{total}] OK   {uid}")
            else:
                failed.append(uid)
                print(f"[{i}/{total}] FAIL {uid} {err or ''}")
    print(f"\n{'='*50}")
    print(f"[*] Working: {len(working)}")
    print(f"[*] Failed : {len(failed)}")
    print(f"{'='*50}\n")
    if failed:
        print("[*] Failed list:")
        for u in failed:
            print(f"    - {u}")
        print()
    return working


def stats_by_level(working):
    if not working:
        print("[!] No working accounts")
        return
    print("[*] Fetching info + level for each account...\n")
    level_count = {}
    ok = 0
    fail = 0
    total = len(working)
    with ThreadPoolExecutor(max_workers=LOGIN_WORKERS) as ex:
        futures = {ex.submit(get_player_info, w["uid"], w["jwt"]): w for w in working}
        done = 0
        for f in as_completed(futures):
            done += 1
            w = futures[f]
            uid = w["uid"]
            try:
                nick, likes, level = f.result()
            except Exception:
                nick, likes, level = None, 0, 0
            if nick is not None:
                ok += 1
                level_count[level] = level_count.get(level, 0) + 1
                print(f"[{done}/{total}] {uid} -> {nick} | lvl={level} | likes={likes}")
            else:
                fail += 1
                print(f"[{done}/{total}] {uid} -> FAILED")
    print(f"\n[*] Info ok={ok} fail={fail}")
    print("[*] Accounts per level:")
    for lvl in sorted(level_count.keys()):
        print(f"    lvl {lvl}: {level_count[lvl]} accounts")
    print()


def like_target(target_uid, working):
    if not working:
        print("[!] No tokens")
        return
    jwts = [w["jwt"] for w in working]
    print(f"\n[*] Target: {target_uid}")
    print(f"[*] Using {len(jwts)} tokens\n")
    nick, before, after, sent = send_likes_once(target_uid, jwts)
    if nick is None:
        print(f"[!] Failed to fetch target {target_uid}")
        return
    print(f"\n{'='*50}")
    print(f"  Target : {nick}")
    print(f"  UID    : {target_uid}")
    print(f"  Before : {before}")
    print(f"  After  : {after}")
    print(f"  Gained : {after - before}")
    print(f"  Sent   : {sent}/{len(jwts)}")
    print(f"{'='*50}\n")


def main():
    print()
    working = check_all_accounts()
    if not working:
        print("[!] No working accounts")
        return
    stats_by_level(working)
    while True:
        target = input("\n - Target : ").strip()
        if target.lower() == 'q':
            break
        if not target.isdigit():
            print("[!] UID numeric only")
            continue
        like_target(target, working)


if __name__ == '__main__':
    main()
