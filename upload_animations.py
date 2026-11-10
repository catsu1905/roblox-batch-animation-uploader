#!/usr/bin/env python3
"""
Batch Animation Uploader
Upload banyak file animasi (.rbxm / .rbxmx) ke Roblox sekaligus lewat Open Cloud Assets API.

Cara pakai (paling gampang): jalankan, lalu ikuti pertanyaannya.
Atau lewat command line:
    python upload_animations.py "C:\\folder\\animasi" --user 123456
    python upload_animations.py "C:\\folder\\animasi" --group 987654

API key bisa lewat env ROBLOX_API_KEY, atau diketik saat diminta (tidak ditampilkan).
"""

import argparse
import getpass
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Module 'requests' belum ada. Jalankan: pip install requests")

API = os.environ.get("ROBLOX_API_BASE", "https://apis.roblox.com/assets/v1")
CONFIG_PATH = Path.home() / ".batch_animation_uploader.json"
MAX_BYTES = 20 * 1024 * 1024
POLL_TRIES = 40

HINTS = {
    401: "API key salah atau sudah expired.",
    403: "Permission key kurang (butuh Assets: Read + Write), atau key dibatasi IP / bukan milik group yang dituju.",
    404: "Endpoint atau ID tujuan tidak ditemukan. Cek User/Group ID.",
}


# ----------------------------------------------------------------------------
# Helper UI
# ----------------------------------------------------------------------------

def pause_and_exit(code=0):
    if getattr(sys, "frozen", False) or INTERACTIVE:
        try:
            input("\nTekan Enter untuk keluar...")
        except EOFError:
            pass
    sys.exit(code)


def fail(msg):
    print(f"\n[!] {msg}")
    pause_and_exit(1)


def clean_path(text: str) -> str:
    return text.strip().strip('"').strip("'").strip()


# ----------------------------------------------------------------------------
# Config (hanya owner; key hanya disimpan kalau user setuju)
# ----------------------------------------------------------------------------

def load_config():
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(cfg):
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        try:
            os.chmod(CONFIG_PATH, 0o600)
        except Exception:
            pass
    except Exception as e:
        print(f"(Gagal simpan pengaturan: {e})")


# ----------------------------------------------------------------------------
# Upload
# ----------------------------------------------------------------------------

def error_text(res):
    try:
        body = res.json()
        msg = body.get("message") or body
    except Exception:
        msg = res.text[:300]
    hint = HINTS.get(res.status_code)
    return f"HTTP {res.status_code}: {msg}" + (f"  -> {hint}" if hint else "")


def upload_one(path: Path, key: str, owner_type: str, owner_id: str):
    """Return (asset_id, error)."""
    ctype = "model/x-rbxmx" if path.suffix.lower() == ".rbxmx" else "model/x-rbxm"
    owner_key = "groupId" if owner_type == "group" else "userId"
    request = {
        "assetType": "Animation",
        "displayName": path.stem[:50],
        "description": "Uploaded with Batch Animation Uploader",
        "creationContext": {"creator": {owner_key: str(owner_id)}},
    }
    headers = {"x-api-key": key}

    res = None
    for attempt in range(4):
        try:
            with open(path, "rb") as f:
                res = requests.post(
                    f"{API}/assets",
                    headers=headers,
                    files={
                        "request": (None, json.dumps(request), "application/json"),
                        "fileContent": (path.name, f, ctype),
                    },
                    timeout=120,
                )
        except requests.RequestException as e:
            return None, f"Koneksi gagal: {e}"
        if res.status_code == 429:
            time.sleep(2 * (attempt + 1))
            continue
        break

    if res is None or not res.ok:
        return None, error_text(res) if res is not None else "Tidak ada respon"

    op = res.json()
    for _ in range(POLL_TRIES):
        if op.get("done"):
            if "error" in op:
                return None, str(op["error"].get("message", op["error"]))
            resp = op.get("response", {})
            asset_id = resp.get("assetId")
            if not asset_id and resp.get("path"):
                asset_id = resp["path"].split("/")[-1]
            if asset_id:
                return str(asset_id), None
            return None, "Selesai tapi asset ID tidak ketemu"
        time.sleep(1)
        try:
            poll = requests.get(f"{API}/{op['path']}", headers=headers, timeout=60)
        except requests.RequestException as e:
            return None, f"Koneksi gagal: {e}"
        if not poll.ok:
            return None, error_text(poll)
        op = poll.json()
    return None, "Timeout nunggu proses upload"


def write_outputs(folder: Path, results: dict):
    (folder / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [f"{name} = {info['animationId']}" for name, info in results.items()]
    (folder / "results.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    entries = ",\n".join(
        f"\t[{json.dumps(name, ensure_ascii=False)}] = {json.dumps(info['animationId'])}"
        for name, info in results.items()
    )
    lua = (
        "local RS = game:GetService('ReplicatedStorage')\n"
        "local folder = RS:FindFirstChild('UploadedAnimations') or Instance.new('Folder')\n"
        "folder.Name = 'UploadedAnimations'\n"
        "folder.Parent = RS\n"
        "local ids = {\n" + entries + "\n}\n"
        "local count = 0\n"
        "for name, id in pairs(ids) do\n"
        "\tlocal anim = folder:FindFirstChild(name) or Instance.new('Animation')\n"
        "\tanim.Name = name\n"
        "\tanim.AnimationId = id\n"
        "\tanim.Parent = folder\n"
        "\tcount += 1\n"
        "end\n"
        "print('Selesai bikin/update', count, 'Animation di ReplicatedStorage.UploadedAnimations')\n"
    )
    (folder / "results.lua").write_text(lua, encoding="utf-8")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

INTERACTIVE = False


def main():
    global INTERACTIVE

    ap = argparse.ArgumentParser(description="Batch upload animasi .rbxm ke Roblox")
    ap.add_argument("folder", nargs="?", help="Folder berisi file .rbxm / .rbxmx")
    who = ap.add_mutually_exclusive_group()
    who.add_argument("--user", help="User ID tujuan upload")
    who.add_argument("--group", help="Group ID tujuan upload")
    args = ap.parse_args()

    INTERACTIVE = args.folder is None

    print("=== Batch Animation Uploader ===\n")
    cfg = load_config()

    # --- folder
    folder_text = args.folder
    if not folder_text:
        folder_text = clean_path(input("Drag folder animasi ke jendela ini (atau ketik path), lalu Enter:\n> "))
    folder = Path(clean_path(folder_text))
    if not folder.is_dir():
        fail(f"Folder tidak ketemu: {folder}")

    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in (".rbxm", ".rbxmx"))
    if not files:
        fail("Tidak ada file .rbxm / .rbxmx di folder itu.")
    print(f"Ketemu {len(files)} file.\n")

    # --- owner
    owner_type, owner_id = None, None
    if args.group:
        owner_type, owner_id = "group", args.group
    elif args.user:
        owner_type, owner_id = "user", args.user
    elif cfg.get("ownerId") and cfg.get("ownerType") in ("user", "group"):
        label = "Group" if cfg["ownerType"] == "group" else "User"
        again = input(f"Upload ke {label} ID {cfg['ownerId']} lagi? (Y/n): ").strip().lower()
        if again in ("", "y", "ya", "yes"):
            owner_type, owner_id = cfg["ownerType"], cfg["ownerId"]
    if not owner_id:
        choice = input("Upload ke (u)ser sendiri atau (g)roup? [u]: ").strip().lower()
        owner_type = "group" if choice.startswith("g") else "user"
        owner_id = input(f"{owner_type.capitalize()} ID (angka): ").strip()
    if not str(owner_id).isdigit():
        fail("ID harus angka.")
    cfg["ownerType"], cfg["ownerId"] = owner_type, str(owner_id)

    # --- key
    key = os.environ.get("ROBLOX_API_KEY") or cfg.get("apiKey", "")
    if not key:
        print("\nPaste API key lalu Enter (tidak akan tampil di layar, itu normal).")
        key = getpass.getpass("API key: ").strip()
        if not key:
            fail("API key kosong.")
        if INTERACTIVE:
            save = input("Simpan key di komputer ini supaya nggak ngetik lagi? (y/N): ").strip().lower()
            if save in ("y", "ya", "yes"):
                cfg["apiKey"] = key
    save_config(cfg)

    # --- resume
    results_path = folder / "results.json"
    results = {}
    if results_path.exists():
        try:
            results = json.loads(results_path.read_text(encoding="utf-8"))
        except Exception:
            results = {}

    print()
    ok_count, fail_count = 0, 0
    for i, path in enumerate(files, 1):
        name = path.stem
        prefix = f"[{i}/{len(files)}] {path.name}"
        if name in results:
            print(f"{prefix} -> skip (sudah ada: {results[name]['animationId']})")
            continue
        if path.stat().st_size > MAX_BYTES:
            print(f"{prefix} -> GAGAL: lebih dari 20 MB")
            fail_count += 1
            continue

        asset_id, err = upload_one(path, key, owner_type, owner_id)
        if asset_id:
            results[name] = {"assetId": asset_id, "animationId": f"rbxassetid://{asset_id}"}
            write_outputs(folder, results)  # simpan tiap sukses
            print(f"{prefix} -> OK rbxassetid://{asset_id}")
            ok_count += 1
        else:
            print(f"{prefix} -> GAGAL: {err}")
            fail_count += 1
            if err and ("HTTP 401" in err or "HTTP 403" in err):
                print("\nBerhenti: masalah autentikasi/permission, file lain pasti gagal juga.")
                break
        time.sleep(0.5)

    print(f"\nSelesai: {ok_count} berhasil, {fail_count} gagal.")
    if results:
        write_outputs(folder, results)
        print(f"\nHasil di folder animasi lu:")
        print(f"  results.txt  -> daftar nama = ID")
        print(f"  results.lua  -> paste ke Command Bar Studio untuk bikin semua Animation otomatis")
    pause_and_exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDibatalkan.")
        sys.exit(130)
