#!/usr/bin/env python3
"""
Batch Animation Uploader
Upload banyak file animasi (.rbxm) ke Roblox sekaligus lewat Open Cloud Assets API.

Jalankan:  python BatchAnimationUploader.py
Browser terbuka otomatis di http://127.0.0.1:8765
Hanya butuh Python 3.8+ (tanpa install library apa pun).

Server ini jalan lokal di PC kamu saja. Dia cuma jadi perantara ke Roblox karena
browser tidak boleh memanggil Open Cloud langsung (CORS). API key tidak disimpan
ke disk kecuali kamu centang "Ingat config di browser ini".
"""
import json
import os
import sys
import threading
import uuid
import webbrowser
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

PORT = 8765
API = os.environ.get("ROBLOX_API_BASE", "https://apis.roblox.com/assets/v1")
MAX_BODY = 25 * 1024 * 1024  # batas Roblox 20 MB + sedikit toleransi

HINTS = {
    401: "API key salah atau sudah expired.",
    403: "Izin key kurang (butuh Assets: Read + Write), key dibatasi IP, atau bukan milik group yang dituju.",
    404: "ID tujuan tidak ditemukan. Cek User/Group ID.",
}

HTML = r"""<!doctype html>
<html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Batch Animation Uploader</title>
<style>
:root{--bg:#14161c;--card:#1c1f27;--line:#2b2f3a;--fg:#e8eaf0;--mut:#8b91a1;--acc:#4f8cff;--ok:#3ecf8e;--err:#ff6b6b}
@media (prefers-color-scheme:light){:root{--bg:#f4f5f8;--card:#fff;--line:#dfe2ea;--fg:#1b1e26;--mut:#6a7183}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}
main{max-width:820px;margin:0 auto;padding:24px 16px 60px}
h1{font-size:22px;margin:0 0 4px}p.s{color:var(--mut);margin:0 0 20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:16px}
h2{font-size:14px;margin:0 0 12px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut)}
label{display:block;font-size:13px;color:var(--mut);margin:10px 0 4px}
input,select,textarea{width:100%;padding:9px 10px;border-radius:8px;border:1px solid var(--line);background:var(--bg);color:var(--fg);font:inherit}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media(max-width:560px){.row{grid-template-columns:1fr}}
.chk{display:flex;gap:8px;align-items:center;margin-top:10px;color:var(--mut);font-size:13px}.chk input{width:auto}
#drop{border:2px dashed var(--line);border-radius:12px;padding:28px;text-align:center;color:var(--mut);cursor:pointer}
#drop.over{border-color:var(--acc);color:var(--acc)}
button{background:var(--acc);color:#fff;border:0;border-radius:8px;padding:10px 16px;font:inherit;font-weight:600;cursor:pointer}
button.g{background:transparent;border:1px solid var(--line);color:var(--fg)}button:disabled{opacity:.5;cursor:default}
button.x{background:transparent;color:var(--mut);padding:2px 8px;font-weight:400}
table{width:100%;border-collapse:collapse;margin-top:8px;font-size:14px}
td,th{padding:7px 6px;border-bottom:1px solid var(--line);text-align:left}th{color:var(--mut);font-weight:500}
.st-ok{color:var(--ok)}.st-err{color:var(--err)}.st-w{color:var(--mut)}td.id{font-family:ui-monospace,monospace}
textarea{font-family:ui-monospace,monospace;font-size:12px;height:150px}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;align-items:center}
#sum{color:var(--mut);font-size:13px;margin-left:auto}
footer{color:var(--mut);font-size:12px;text-align:center;margin-top:24px}
</style></head><body><main>
<h1>Batch Animation Uploader</h1>
<p class="s">Upload banyak file .rbxm (KeyframeSequence) jadi Animation di Roblox. Nama asset = nama file.</p>

<div class="card"><h2>Config</h2>
<label>Open Cloud API Key (butuh izin <code>Assets API: Read &amp; Write</code>)</label>
<input id="key" type="password" placeholder="API key milikmu sendiri" autocomplete="off">
<div class="row">
 <div><label>Upload sebagai</label><select id="ctype"><option value="userId">User (akun pribadi)</option><option value="groupId">Group</option></select></div>
 <div><label>User ID / Group ID</label><input id="cid" inputmode="numeric" placeholder="contoh: 123456789"></div>
</div>
<label>Deskripsi (opsional)</label><input id="desc" placeholder="Animation">
<label>Prefix nama (opsional)</label><input id="prefix" placeholder="mis. Sword_">
<div class="chk"><input type="checkbox" id="rem"><label style="margin:0">Ingat config di browser ini (API key ikut tersimpan di localStorage)</label></div>
</div>

<div class="card"><h2>File</h2>
<div id="drop">Drop file .rbxm di sini atau klik untuk pilih<input id="files" type="file" accept=".rbxm,.rbxmx" multiple hidden></div>
<table id="tbl" hidden><thead><tr><th>Nama</th><th>Status</th><th>Asset ID</th><th></th></tr></thead><tbody></tbody></table>
<div class="bar"><button id="go" disabled>Upload semua</button><button class="g" id="clr">Kosongkan</button><span id="sum"></span></div>
</div>

<div class="card" id="out" hidden><h2>Hasil</h2>
<label>Script Studio (paste ke Command Bar) — bikin folder Animation dengan nama sesuai file</label>
<textarea id="lua" readonly></textarea>
<div class="bar"><button class="g" id="cl">Copy script</button><button class="g" id="cn">Copy daftar</button><button class="g" id="cj">Copy JSON</button><button class="g" id="dj">Download JSON</button></div>
</div>
<footer>Server lokal jalan di komputer kamu. Tutup jendela terminal untuk menghentikannya.</footer>
</main>
<script>
const $=s=>document.querySelector(s);
const KEY="rbxmUploaderCfg",MAX=20*1024*1024;
let items=[],busy=false;
try{const c=JSON.parse(localStorage.getItem(KEY)||"null");if(c){$("#key").value=c.key||"";$("#ctype").value=c.ctype||"userId";$("#cid").value=c.cid||"";$("#desc").value=c.desc||"";$("#prefix").value=c.prefix||"";$("#rem").checked=true}}catch(e){}
function save(){try{if($("#rem").checked)localStorage.setItem(KEY,JSON.stringify({key:$("#key").value,ctype:$("#ctype").value,cid:$("#cid").value,desc:$("#desc").value,prefix:$("#prefix").value}));else localStorage.removeItem(KEY)}catch(e){}}
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));

const drop=$("#drop"),fi=$("#files");
drop.onclick=()=>fi.click();
fi.onchange=()=>{add(fi.files);fi.value=""};
drop.ondragover=e=>{e.preventDefault();drop.classList.add("over")};
drop.ondragleave=()=>drop.classList.remove("over");
drop.ondrop=e=>{e.preventDefault();drop.classList.remove("over");add(e.dataTransfer.files)};

function add(fl){
 for(const f of fl){
  if(!/\.rbxmx?$/i.test(f.name))continue;
  if(items.some(i=>i.file.name===f.name&&i.file.size===f.size))continue;
  const it={file:f,name:f.name.replace(/\.rbxmx?$/i,""),st:"menunggu",cls:"st-w",id:"",skip:false};
  if(f.size>MAX){it.st="terlalu besar (maks 20 MB)";it.cls="st-err";it.skip=true}
  items.push(it)
 }
 render()
}
function render(){
 const t=$("#tbl");t.hidden=!items.length;
 t.tBodies[0].innerHTML=items.map((it,i)=>`<tr><td>${esc(it.name)}</td><td class="${it.cls}">${esc(it.st)}</td><td class="id">${esc(it.id)}</td><td><button class="x" data-i="${i}" ${busy?"disabled":""}>✕</button></td></tr>`).join("");
 const done=items.filter(i=>i.id).length;
 $("#sum").textContent=items.length?`${done}/${items.length} berhasil`:"";
 $("#go").disabled=busy||!items.some(i=>!i.id&&!i.skip);
}
$("#tbl").addEventListener("click",e=>{
 const i=e.target.dataset&&e.target.dataset.i;
 if(i===undefined||busy)return;
 items.splice(+i,1);render();result()
});
$("#clr").onclick=()=>{if(busy)return;items=[];render();$("#out").hidden=true};

async function api(path,opt){
 const r=await fetch(path,opt);
 const j=await r.json().catch(()=>({}));
 if(!r.ok)throw new Error(j.error||("HTTP "+r.status));
 return j
}
async function one(it,h){
 it.st="mengupload…";it.cls="st-w";render();
 const name=($("#prefix").value+it.name).slice(0,50);
 let op=null;
 for(let a=0;a<4;a++){
  try{
   op=await api("/api/upload",{method:"POST",headers:{...h,"X-Name":encodeURIComponent(name),"X-Desc":encodeURIComponent($("#desc").value||"Animation"),"X-Filename":encodeURIComponent(it.file.name)},body:it.file});
   break
  }catch(e){
   if(/HTTP 429/.test(e.message)&&a<3){it.st="kena rate limit, menunggu…";render();await sleep(3000*(a+1));continue}
   throw e
  }
 }
 it.st="diproses…";render();
 for(let k=0;k<40;k++){
  await sleep(1500);
  const s=await api("/api/op?id="+encodeURIComponent(op.path.replace("operations/","")),{headers:h});
  if(s.done){
   if(s.error)throw new Error(s.error.message||JSON.stringify(s.error));
   it.id=String(s.response.assetId);it.st="sukses";it.cls="st-ok";render();return
  }
 }
 throw new Error("timeout menunggu Roblox")
}
$("#go").onclick=async()=>{
 const key=$("#key").value.trim(),cid=$("#cid").value.trim();
 if(!key||!/^\d+$/.test(cid)){alert("Isi API key dan ID (angka) dulu.");return}
 save();busy=true;render();
 const h={"X-Api-Key":key,"X-Creator-Type":$("#ctype").value,"X-Creator-Id":cid};
 for(const it of items){
  if(it.id||it.skip)continue;
  try{await one(it,h)}
  catch(e){
   it.st="gagal: "+e.message;it.cls="st-err";render();
   if(/HTTP 40[13]/.test(e.message)){break} // masalah key/izin: file lain pasti gagal juga
  }
 }
 busy=false;render();result()
};

function result(){
 const ok=items.filter(i=>i.id);
 if(!ok.length){$("#out").hidden=true;return}
 const rows=ok.map(i=>`\t{${JSON.stringify(($("#prefix").value+i.name).slice(0,50))}, ${i.id}},`).join("\n");
 $("#lua").value=`local RS = game:GetService("ReplicatedStorage")\nlocal folder = RS:FindFirstChild("UploadedAnimations") or Instance.new("Folder")\nfolder.Name = "UploadedAnimations"\nfolder.Parent = RS\nlocal list = {\n${rows}\n}\nfor _, e in ipairs(list) do\n\tlocal a = folder:FindFirstChild(e[1]) or Instance.new("Animation")\n\ta.Name = e[1]\n\ta.AnimationId = "rbxassetid://" .. e[2]\n\ta.Parent = folder\nend\nprint("Selesai: " .. #list .. " animasi")`;
 $("#out").hidden=false
}
const finalName=i=>($("#prefix").value+i.name).slice(0,50);
const json=()=>JSON.stringify(Object.fromEntries(items.filter(i=>i.id).map(i=>[finalName(i),"rbxassetid://"+i.id])),null,2);
const list=()=>items.filter(i=>i.id).map(i=>finalName(i)+" = rbxassetid://"+i.id).join("\n");
function copy(btn,text){
 const old=btn.textContent;
 navigator.clipboard.writeText(text).then(()=>{btn.textContent="Tersalin ✓"},()=>{btn.textContent="Gagal copy"});
 setTimeout(()=>btn.textContent=old,1300)
}
$("#cl").onclick=e=>copy(e.target,$("#lua").value);
$("#cn").onclick=e=>copy(e.target,list());
$("#cj").onclick=e=>copy(e.target,json());
$("#dj").onclick=()=>{const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([json()],{type:"application/json"}));a.download="animations.json";a.click()};
</script></body></html>"""


def multipart(fields_json, filename, data, content_type):
    b = "----rbxm" + uuid.uuid4().hex
    parts = [
        f'--{b}\r\nContent-Disposition: form-data; name="request"\r\nContent-Type: application/json\r\n\r\n'.encode(),
        json.dumps(fields_json).encode(),
        f'\r\n--{b}\r\nContent-Disposition: form-data; name="fileContent"; filename="{filename}"\r\nContent-Type: {content_type}\r\n\r\n'.encode(),
        data,
        f"\r\n--{b}--\r\n".encode(),
    ]
    return b"".join(parts), f"multipart/form-data; boundary={b}"


def roblox(method, url, key, body=None, ctype=None):
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("x-api-key", key)
    if ctype:
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            msg = json.loads(raw).get("message") or raw
        except Exception:
            msg = raw
        hint = HINTS.get(e.code)
        text = f"HTTP {e.code}: {msg}" + (f" — {hint}" if hint else "")
        return e.code, {"error": text}
    except Exception as e:
        return 502, {"error": f"Koneksi ke Roblox gagal: {e}"}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, obj, ctype="application/json"):
        data = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def hdr(self, k):
        return unquote(self.headers.get(k, ""))

    def host_ok(self):
        # tolak request dari host lain (mis. DNS rebinding); hanya localhost yang boleh
        return self.headers.get("Host", "").split(":")[0] in ("127.0.0.1", "localhost")

    def do_GET(self):
        if not self.host_ok():
            return self.send(403, {"error": "forbidden"})
        u = urlparse(self.path)
        if u.path == "/":
            return self.send(200, HTML.encode(), "text/html; charset=utf-8")
        if u.path == "/api/op":
            op = parse_qs(u.query).get("id", [""])[0]
            if not op.replace("-", "").isalnum():
                return self.send(400, {"error": "bad id"})
            code, j = roblox("GET", f"{API}/operations/{op}", self.hdr("X-Api-Key"))
            return self.send(code, j)
        self.send(404, {"error": "not found"})

    def do_POST(self):
        if not self.host_ok():
            return self.send(403, {"error": "forbidden"})
        if self.path != "/api/upload":
            return self.send(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length", 0))
        if n <= 0 or n > MAX_BODY:
            return self.send(413, {"error": "file kosong atau lebih dari 20 MB"})
        data = self.rfile.read(n)
        cid = self.hdr("X-Creator-Id")
        ctype = self.hdr("X-Creator-Type")
        if ctype not in ("userId", "groupId") or not cid.isdigit():
            return self.send(400, {"error": "creator tidak valid"})
        req = {
            "assetType": "Animation",
            "displayName": self.hdr("X-Name")[:50],
            "description": self.hdr("X-Desc") or "Animation",
            "creationContext": {"creator": {ctype: cid}},
        }
        fname = self.hdr("X-Filename").replace('"', "").replace("\r", "").replace("\n", "") or "anim.rbxm"
        content_type = "model/x-rbxmx" if fname.lower().endswith(".rbxmx") else "model/x-rbxm"
        body, ct = multipart(req, fname, data, content_type)
        code, j = roblox("POST", f"{API}/assets", self.hdr("X-Api-Key"), body, ct)
        self.send(code, j)


def start_server():
    for port in range(PORT, PORT + 10):
        try:
            return ThreadingHTTPServer(("127.0.0.1", port), H), port
        except OSError:
            continue
    sys.exit(f"Port {PORT}-{PORT + 9} semua dipakai program lain. Tutup salah satunya lalu coba lagi.")


def main():
    srv, port = start_server()
    url = f"http://127.0.0.1:{port}"
    print(f"Batch Animation Uploader jalan di {url}")
    print("Browser akan terbuka otomatis. Tutup jendela ini (atau Ctrl+C) untuk berhenti.")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
