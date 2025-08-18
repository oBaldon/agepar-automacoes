import subprocess, os, glob
from rq import get_current_job

def _run(cmd:list[str]) -> dict:
    subprocess.run(cmd, check=True)
    return {"ok": True}

def _finish(artifact):
    j = get_current_job()
    if j:
        j.meta["artifact"] = artifact
        j.save_meta()
    return {"ok": True, "artifact": artifact}

def run_precos_manual(orc, ref, ref_type, banco, tol_rel, out, **_):
    cmd = ["python","-m","src.cli","run-precos",
           "--orc", orc, "--ref", ref, "--ref-type", ref_type,
           "--banco", banco, "--tol-rel", str(tol_rel), "--out", out]
    _run(cmd)
    return _finish(out)

def run_precos_auto(orc, tol_rel, out_dir, **_):
    cmd = ["python","-m","src.cli","run-precos-auto",
           "--orc", orc, "--tol-rel", str(tol_rel), "--out-dir", out_dir]
    _run(cmd)
    # captura JSONs gerados no diretório
    files = sorted(glob.glob(os.path.join(out_dir, "*.json")))
    return _finish(files or out_dir)

def validar_estrutura(orc, banco_a, base, base_type, out, **_):
    cmd = ["python","-m","src.cli","validar-estrutura",
           "--orc", orc, "--banco-a", banco_a, "--base", base,
           "--base-type", base_type, "--out", out]
    _run(cmd)
    return _finish(out)
