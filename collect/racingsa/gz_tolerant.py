"""Read a (possibly truncated, possibly multi-member) gzip of JSON lines; returns the complete lines that survive.
Usage as script: python3 gz_tolerant.py in.jsonl.gz out.jsonl"""
import sys, zlib, json
def lines(path):
    data = open(path, 'rb').read(); out = []; pos = 0; MAGIC = b'\x1f\x8b\x08'
    while pos < len(data):
        d = zlib.decompressobj(31); chunk = b''
        try: chunk = d.decompress(data[pos:])
        except zlib.error: pass
        out.append(chunk)
        if d.eof: pos = len(data) - len(d.unused_data); continue
        nxt = data.find(MAGIC, pos + 1)                      # broken member: resume at the next gzip header
        if nxt < 0: break
        pos = nxt
    for blob in out:
        for ln in blob.decode('utf-8', 'replace').splitlines():
            try: json.loads(ln); yield ln
            except json.JSONDecodeError: pass                 # a cut-off line
if __name__ == '__main__':
    n = 0
    with open(sys.argv[2], 'w') as fh:
        for ln in lines(sys.argv[1]): fh.write(ln + '\n'); n += 1
    print('kept', n, 'lines')
